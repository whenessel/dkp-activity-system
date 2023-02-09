from __future__ import annotations
from typing import Any, Union, Optional
import os
import platform
import discord
from discord.ext import commands
from django.conf import settings

from evebot.exceptions import NotEventChannel, NotEventModerator
from evebot.utils.functional import search_cogs


class EveContext(commands.Context):
    guild: discord.Guild
    channel: Union[discord.TextChannel, discord.Thread, discord.DMChannel]
    author: discord.Member
    me: discord.Member
    prefix: str
    bot: EveBot

    @discord.utils.cached_property
    def replied_reference(self) -> Optional[discord.MessageReference]:
        ref = self.message.reference
        if ref and isinstance(ref.resolved, discord.Message):
            return ref.resolved.to_reference()
        return None

    @discord.utils.cached_property
    def replied_message(self) -> Optional[discord.Message]:
        ref = self.message.reference
        if ref and isinstance(ref.resolved, discord.Message):
            return ref.resolved
        return None


class EveBot(commands.Bot):
    initial_extensions = []
    settings: Any

    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(
            command_prefix=commands.when_mentioned_or(settings.EVE_PREFIX),
            intents=intents,
            enable_debug_events=True,
        )
        if settings.configured:
            self.settings = settings

    async def get_context(self, message, *, cls=EveContext):
        return await super().get_context(message, cls=cls)

    async def initialization_extensions(self):
        if settings.configured:
            self.initial_extensions = self.initial_extensions + search_cogs(settings.INSTALLED_APPS)
        for cog in self.initial_extensions:
            try:
                await self.load_extension(cog)
                print(f"Loaded extension {cog}")
            except Exception as exc:
                print(f"Could not load extension \'{cog}\' due to {exc.__class__.__name__}: {exc}")

    async def configure_owners(self):
        self.owner_ids = settings.EVE_OWNERS

    async def setup_hook(self):
        await self.initialization_extensions()
        await self.configure_owners()
        # if self.settings.EVE_SYNC_COMMANDS_GLOBALLY:
        #     print("Syncing commands globally...")
        #     await self.tree.sync()

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print(f"discord.py API version: {discord.__version__}")
        print(f"Python version: {platform.python_version()}")
        print(f"Running on: {platform.system()} {platform.release()} ({os.name})")

    async def on_message(self, message: discord.Message) -> None:
        if message.author == self.user or message.author.bot:
            return
        await self.process_commands(message)

    # async def on_command_error(self, ctx: EveContext, error: commands.CommandError) -> None:
    #     if isinstance(error, commands.NoPrivateMessage):
    #         await ctx.author.send("Эта команда не может быть использована в приват сообщении.")
    #     elif isinstance(error, commands.DisabledCommand):
    #         await ctx.author.send("Прости, команда не активна.")
    #     elif isinstance(error, commands.CommandInvokeError):
    #         original = error.original
    #         # if not isinstance(original, discord.HTTPException):
    #         #     print("In %s:", ctx.command.qualified_name, exc_info=original)
    #         print(ctx.command.qualified_name, str(error))
    #     elif isinstance(error, commands.ArgumentParsingError):
    #         await ctx.send(str(error))
    #     elif isinstance(error, NotEventChannel):
    #         await ctx.author.send(f"Прости, этот канал не подходит для создания событий.")
    #     elif isinstance(error, NotEventModerator):
    #         await ctx.author.send(f"Пошел прочь! У тебя нет прав для использования этой команды.")
    #     else:
    #         raise error
