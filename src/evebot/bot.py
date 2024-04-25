import datetime
import logging
import os
import platform
import typing as t
from collections import Counter, defaultdict

import aiohttp
import discord
from discord.ext import commands
from django.conf import settings

from evebot.context import EveContext
from evebot.utils.functional import find_cogs
from evebot.utils.storage import PersistJsonFile

description = """
Hello! I am a "EVE" bot to provide some nice features.
"""

logger = logging.getLogger(__name__)


discord.utils.setup_logging(level=logging.INFO, root=True)


def _prefix_callable(bot: "EveBot", msg: discord.Message):
    user_id = bot.user.id
    base = [f"<@!{user_id}> ", f"<@{user_id}> "]
    if msg.guild is None:
        base.append(settings.EVE_PREFIX)
    else:
        base.extend(bot.prefixes.get(msg.guild.id, settings.EVE_PREFIX))
    return base


class ProxyObject(discord.Object):
    def __init__(self, guild: t.Optional[discord.abc.Snowflake]):
        super().__init__(id=0)
        self.guild: t.Optional[discord.abc.Snowflake] = guild


class EveBot(commands.AutoShardedBot):
    user: discord.ClientUser
    command_stats: Counter[str]
    socket_stats: Counter[str]
    command_types_used: Counter[bool]
    logging_handler: t.Any
    bot_app_info: discord.AppInfo
    old_tree_error = t.Callable[
        [discord.Interaction, discord.app_commands.AppCommandError],
        t.Coroutine[t.Any, t.Any, None],
    ]

    session: t.Optional[aiohttp.ClientSession] = None

    prefixes: PersistJsonFile[list[str]]
    blacklist: PersistJsonFile[bool]

    uptime: t.Optional[datetime.datetime]

    def __init__(self):
        allowed_mentions = discord.AllowedMentions(
            roles=True, everyone=True, users=True
        )
        intents = discord.Intents.all()

        super().__init__(
            command_prefix=_prefix_callable,
            description=description,
            pm_help=None,
            help_attrs=dict(hidden=True),
            chunk_guilds_at_startup=False,
            heartbeat_timeout=120.0,
            allowed_mentions=allowed_mentions,
            intents=intents,
            enable_debug_events=True,
        )
        self.client_id: str = settings.EVE_CLIENT_ID
        self.resumes: defaultdict[int, list[datetime.datetime]] = defaultdict(list)
        self.identifies: defaultdict[int, list[datetime.datetime]] = defaultdict(list)
        self.spam_control = commands.CooldownMapping.from_cooldown(
            10, 30.0, commands.BucketType.user
        )
        self._auto_spam_count = Counter()

    async def configure_owners(self):
        self.owner_ids = settings.EVE_OWNERS

    async def setup_hook(self) -> None:
        self.session = aiohttp.ClientSession()
        # guild_id: list
        self.prefixes: PersistJsonFile[list[str]] = PersistJsonFile(
            settings.SECRET_ROOT / "prefixes.json"
        )

        # guild_id and user_id mapped to True
        # these are users and guilds globally blacklisted
        # from using the bot
        self.blacklist: PersistJsonFile[bool] = PersistJsonFile(
            settings.SECRET_ROOT / "blacklist.json"
        )

        self.bot_app_info = await self.application_info()
        self.owner_id = self.bot_app_info.owner.id
        await self.configure_owners()
        logger.info(f"EveBot owners: {self.owner_ids}")

        logger.info("Search installed extensions...")
        installed_extensions = find_cogs(settings.INSTALLED_APPS)

        logger.info("Extension loading extensions...")
        for installed_ext in installed_extensions:
            logger.info(f"Loading extension {installed_ext}...")
            try:
                await self.load_extension(installed_ext)
                logger.info(f'Extension loaded: "{installed_ext}"')
            except Exception as exc:
                logger.error(
                    f"Failed to load extension {installed_ext}.", exc_info=False
                )
                logger.debug(
                    f"Failed to load extension {installed_ext} with {exc}",
                    exc_info=True,
                )
            # await self.load_extension(installed_ext)

        if settings.EVE_SYNC_COMMANDS_GLOBALLY:
            logger.info("Syncing commands globally...")
            await self.tree.sync()

        logger.info("EveBot setup complete")

    @property
    def prefix(self) -> str:
        return settings.EVE_PREFIX

    @property
    def owner(self) -> discord.User:
        return self.bot_app_info.owner

    def _clear_gateway_data(self) -> None:
        one_week_ago = discord.utils.utcnow() - datetime.timedelta(days=7)
        for shard_id, dates in self.identifies.items():
            to_remove = [index for index, dt in enumerate(dates) if dt < one_week_ago]
            for index in reversed(to_remove):
                del dates[index]

        for shard_id, dates in self.resumes.items():
            to_remove = [index for index, dt in enumerate(dates) if dt < one_week_ago]
            for index in reversed(to_remove):
                del dates[index]

    async def _call_before_identify_hook(
        self, shard_id: t.Optional[int], *, initial: bool = False
    ) -> None:
        self._clear_gateway_data()
        self.identifies[shard_id].append(discord.utils.utcnow())
        await super().before_identify_hook(shard_id, initial=initial)

    async def on_command_error(
        self, ctx: EveContext, error: commands.CommandError
    ) -> None:
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.author.send("This command cannot be used in private messages.")
            # log.error("This command cannot be used in private messages.")
        elif isinstance(error, commands.DisabledCommand):
            await ctx.author.send("Sorry. This command is disabled and cannot be used.")
            # log.error("Sorry. This command is disabled and cannot be used.")
        elif isinstance(error, commands.CommandInvokeError):
            original = error.original
            if not isinstance(original, discord.HTTPException):
                logger.exception(f"In {ctx.command.qualified_name}:", exc_info=original)
        elif isinstance(error, commands.ArgumentParsingError):
            await ctx.send(str(error))

        logger.error(str(error))

    def get_guild_prefixes(
        self, guild: t.Optional[discord.abc.Snowflake], *, local_inject=_prefix_callable
    ) -> list[str]:
        proxy_msg = ProxyObject(guild)
        return local_inject(self, proxy_msg)  # type: ignore  # lying

    def get_raw_guild_prefixes(self, guild_id: int) -> list[str]:
        return self.prefixes.get(guild_id, settings.EVE_PREFIX)

    async def set_guild_prefixes(
        self, guild: discord.abc.Snowflake, prefixes: list[str]
    ) -> None:
        if len(prefixes) == 0:
            await self.prefixes.put(guild.id, [])
        elif len(prefixes) > 10:
            raise RuntimeError("Cannot have more than 10 custom prefixes.")
        else:
            await self.prefixes.put(guild.id, sorted(set(prefixes), reverse=True))

    async def add_to_blacklist(self, object_id: int):
        await self.blacklist.put(object_id, True)

    async def remove_from_blacklist(self, object_id: int):
        try:
            await self.blacklist.remove(object_id)
        except KeyError:
            pass

    async def query_member_named(
        self, guild: discord.Guild, argument: str, *, cache: bool = False
    ) -> t.Optional[discord.Member]:
        """Queries a member by their name, name + discrim, or nickname.

        Parameters
        ------------
        guild: Guild
            The guild to query the member in.
        argument: str
            The name, nickname, or name + discrim combo to check.
        cache: bool
            Whether to cache the results of the query.

        Returns
        ---------
        Optional[Member]
            The member matching the query or None if not found.
        """
        if len(argument) > 5 and argument[-5] == "#":
            username, _, discriminator = argument.rpartition("#")
            members = await guild.query_members(username, limit=100, cache=cache)
            return discord.utils.get(
                members, name=username, discriminator=discriminator
            )
        else:
            members = await guild.query_members(argument, limit=100, cache=cache)
            return discord.utils.find(
                lambda m: m.name == argument or m.nick == argument, members
            )

    async def get_or_fetch_member(
        self, guild: discord.Guild, member_id: int
    ) -> t.Optional[discord.Member]:
        """Looks up a member in cache or fetches if not found.

        Parameters
        -----------
        guild: Guild
            The guild to look in.
        member_id: int
            The member ID to search for.

        Returns
        ---------
        Optional[Member]
            The member or None if not found.
        """

        member = guild.get_member(member_id)
        if member is not None:
            return member

        shard: discord.ShardInfo = self.get_shard(guild.shard_id)
        if shard.is_ws_ratelimited():
            try:
                member = await guild.fetch_member(member_id)
            except discord.HTTPException:
                return None
            else:
                return member

        members = await guild.query_members(limit=1, user_ids=[member_id], cache=True)
        if not members:
            return None
        return members[0]

    async def resolve_member_ids(
        self, guild: discord.Guild, member_ids: t.Iterable[int]
    ) -> t.AsyncIterator[discord.Member]:
        """Bulk resolves member IDs to member instances, if possible.

        Members that can't be resolved are discarded from the list.

        This is done lazily using an asynchronous iterator.

        Note that the order of the resolved members is not the same as the input.

        Parameters
        -----------
        guild: Guild
            The guild to resolve from.
        member_ids: Iterable[int]
            An iterable of member IDs.

        Yields
        --------
        Member
            The resolved members.
        """

        needs_resolution = []
        for member_id in member_ids:
            member = guild.get_member(member_id)
            if member is not None:
                yield member
            else:
                needs_resolution.append(member_id)

        total_need_resolution = len(needs_resolution)
        if total_need_resolution == 1:
            shard: discord.ShardInfo = self.get_shard(guild.shard_id)
            if shard.is_ws_ratelimited():
                try:
                    member = await guild.fetch_member(needs_resolution[0])
                except discord.HTTPException:
                    pass
                else:
                    yield member
            else:
                members = await guild.query_members(
                    limit=1, user_ids=needs_resolution, cache=True
                )
                if members:
                    yield members[0]
        elif total_need_resolution <= 100:
            # Only a single resolution call needed here
            resolved = await guild.query_members(
                limit=100, user_ids=needs_resolution, cache=True
            )
            for member in resolved:
                yield member
        else:
            # We need to chunk these in bits of 100...
            for index in range(0, total_need_resolution, 100):
                to_resolve = needs_resolution[index : index + 100]
                members = await guild.query_members(
                    limit=100, user_ids=to_resolve, cache=True
                )
                for member in members:
                    yield member

    async def on_ready(self):
        if not hasattr(self, "uptime"):
            self.uptime = discord.utils.utcnow()

        logger.info(f"Discord.py API version: {discord.__version__}")
        logger.info(f"Python version: {platform.python_version()}")
        logger.info(f"Running on: {platform.system()} {platform.release()} ({os.name})")
        logger.info(f'Ready: logged in as "{self.user}" (ID: {self.user.id})')

    async def on_shard_resumed(self, shard_id: int):
        logger.info("Shard ID %s has resumed...", shard_id)
        self.resumes[shard_id].append(discord.utils.utcnow())

    async def log_spammer(
        self,
        ctx: EveContext,
        message: discord.Message,
        retry_after: float,
        *,
        auto_block: bool = False,
    ):
        guild_name = getattr(ctx.guild, "name", "No Guild (DMs)")
        guild_id = getattr(ctx.guild, "id", None)
        fmt = "User %s (ID %s) in guild %r (ID %s) spamming, retry_after: %.2fs"
        logger.warning(
            fmt, message.author, message.author.id, guild_name, guild_id, retry_after
        )
        if not auto_block:
            return

    async def get_context(
        self,
        origin: t.Union[discord.Interaction, discord.Message],
        /,
        *,
        cls=EveContext,
    ) -> EveContext:
        return await super().get_context(origin, cls=cls)

    async def process_commands(self, message: discord.Message):
        ctx = await self.get_context(message)

        if ctx.command is None:
            return

        if ctx.author.id in self.blacklist:
            return

        if ctx.guild is not None and ctx.guild.id in self.blacklist:
            return

        bucket = self.spam_control.get_bucket(message)
        current = message.created_at.timestamp()
        retry_after = bucket and bucket.update_rate_limit(current)
        author_id = message.author.id
        if retry_after and author_id != self.owner_id:
            self._auto_spam_count[author_id] += 1
            if self._auto_spam_count[author_id] >= 5:
                await self.add_to_blacklist(author_id)
                del self._auto_spam_count[author_id]
                await self.log_spammer(ctx, message, retry_after, auto_block=True)
            else:
                await self.log_spammer(ctx, message, retry_after)
            return
        else:
            self._auto_spam_count.pop(author_id, None)

        await self.invoke(ctx)

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        await self.process_commands(message)

    async def on_guild_join(self, guild: discord.Guild) -> None:
        if guild.id in self.blacklist:
            await guild.leave()

    async def close(self) -> None:
        await super().close()
        if self.session:
            await self.session.close()
