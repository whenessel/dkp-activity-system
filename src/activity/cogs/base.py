import enum
import logging
import typing as t

import discord
from discord import app_commands
from discord.app_commands.errors import CommandAlreadyRegistered
from discord.ext import commands, tasks
from django.db.models import Count
from enum_properties import EnumProperties, s

from activity.choices import AttendanceServer, EventStatus
from activity.models import Event, EventAttendance, EventChannel, EventModerator
from evebot.bot import EveBot, EveContext
from evebot.utils.enums import EmojiEnumMIxin


logger = logging.getLogger(__name__)


class MemberReactions(
    EmojiEnumMIxin, EnumProperties, s("emoji"), s("attend_server", case_fold=True)
):
    ONE = enum.auto(), "1️⃣", AttendanceServer.ONE
    TWO = enum.auto(), "2️⃣", AttendanceServer.TWO
    THREE = enum.auto(), "3️⃣", AttendanceServer.THREE
    FOUR = enum.auto(), "4️⃣", AttendanceServer.FOUR
    FIVE = enum.auto(), "5️⃣", AttendanceServer.FIVE
    SIX = enum.auto(), "6️⃣", AttendanceServer.SIX


class QuantityModal(discord.ui.Modal):
    quantity = discord.ui.TextInput(
        label="Количество минут или количество боссов",
        placeholder="1",
        required=True,
        style=discord.TextStyle.short,
    )

    def __init__(self, cog: "BaseEventCog", event: "EventItem"):
        self.cog = cog
        self.event = event
        super().__init__(title=f"{event.title} ({event.id})", timeout=None)

        self.quantity.placeholder = str(event.capacity)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        quantity = int(self.quantity.value)
        await self.event.do_finish(quantity=quantity)
        embed = event_embed(event=self.event)
        message = await self.event.fetch_message()
        await self.event.clean_reactions()
        await interaction.followup.edit_message(
            message_id=message.id, embed=embed, view=None
        )


def event_template_embed(title: str, description: str) -> discord.Embed:
    embed = discord.Embed(colour=discord.Colour.blue())
    embed.title = f"{title}"
    embed.description = f"{description}"
    return embed


def event_embed(event: "EventItem") -> discord.Embed:
    colour = discord.Colour.light_gray()
    if event.status == EventStatus.STARTED:
        colour = discord.Colour.blue()
    elif event.status == EventStatus.CANCELED:
        colour = discord.Colour.red()
    elif event.status == EventStatus.FINISHED:
        colour = discord.Colour.green()
    elif event.status == EventStatus.DELETED:
        colour = discord.Colour.dark_grey()

    embed = discord.Embed(colour=colour)

    embed.title = f"[{event.get_status_display().upper()}] {event.title.upper()}"

    avatar_url = ""
    try:
        avatar_url = event.author.display_avatar.url
    except Exception:
        logger.error(f"Can't get display_avatar for user: {event.author}")

    embed.set_author(
        name=f"РЛ: {event.author.display_name}",
        icon_url=avatar_url,  # event.author.avatar.url
    )

    embed.add_field(name="Время сбора", value=f"{event.description}", inline=False)
    embed.add_field(name="", value="", inline=False)
    embed.add_field(name="Номер события", value=f"{event.id}", inline=True)
    embed.add_field(
        name="Время события",
        value=f'{event.created.strftime("%d.%m.%Y %H:%M")}',
        inline=True,
    )
    embed.add_field(name="", value="", inline=False)

    embed.add_field(name="Призыв", value="@everyone")

    embed.set_footer(
        text=f"{MemberReactions.ONE.emoji}    "
        f"{MemberReactions.ONE.attend_server.label}\n"
        f"{MemberReactions.TWO.emoji}    "
        f"{MemberReactions.TWO.attend_server.label}\n"
        f"{MemberReactions.THREE.emoji}    "
        f"{MemberReactions.THREE.attend_server.label}\n"
        f"{MemberReactions.FOUR.emoji}    "
        f"{MemberReactions.FOUR.attend_server.label}\n"
        f"{MemberReactions.FIVE.emoji}    "
        f"{MemberReactions.FIVE.attend_server.label}\n"
        f"{MemberReactions.SIX.emoji}    "
        f"{MemberReactions.SIX.attend_server.label}\n"
    )

    if event.status == EventStatus.FINISHED:
        # guild_members = list([member for member in event.guild.members])
        stats_footer = ""

        for item in event.event_attendances.values("server").annotate(Count("server")):
            mr = MemberReactions[item["server"]]
            cnt = item["server__count"]
            stats_footer += f"{mr.emoji}    {mr.attend_server.label}    {cnt}\n"

        embed.set_footer(text=stats_footer)

    return embed


class EventItem(Event):
    bot: t.Optional[EveBot] = None
    cog: t.Optional["BaseEventCog"] = None

    message: t.Optional[discord.Message]
    author: t.Optional[discord.Member]

    _member_attendances: dict[int, AttendanceServer] = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def save(
        self,
        message_id=None,
        status=None,
        force_insert=False,
        force_update=False,
        using=None,
        update_fields=None,
    ):
        if message_id:
            self.message_id = message_id
        if status:
            self.status = status
        super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )

    class Meta:
        proxy = True

    @property
    def guild(self) -> t.Optional[discord.Guild]:
        if self.guild_id is not None:
            return self.bot.get_guild(self.guild_id)
        return None

    @property
    def channel(self) -> t.Optional[discord.TextChannel]:
        if self.channel_id is not None:
            return self.bot.get_channel(self.channel_id)
        return None

    @property
    def author(self) -> discord.Member:
        return self.guild.get_member(self.member_id)

    async def fetch_message(self) -> t.Optional[discord.Message]:
        channel = self.channel
        if channel is not None and self.message_id is not None:
            self.message = await self.cog.get_event_message(channel.id, self.message_id)
        return self.message

    @property
    def member_attendances(self) -> dict:
        # Подгружаем из БД то что есть ( при рестарте )
        if not self._member_attendances:
            members = self.event_attendances.all().values("member_id", "server")
            for member in members:
                attend_server = AttendanceServer(member["server"])
                self._member_attendances[member["member_id"]] = attend_server
        return self._member_attendances

    def member_attendance(self, member_id: int):
        attend_server = self.member_attendances.get(member_id)
        return attend_server

    def add_member_attendance(
        self, member: discord.Member, server: AttendanceServer, force: bool = True
    ) -> t.Tuple[EventAttendance, bool]:
        self._member_attendances[member.id] = server
        attend_member, created = EventAttendance.objects.get_or_create(
            event=self,
            member_id=member.id,
            defaults={
                "member_name": member.name,
                "member_display_name": member.display_name,
                "server": server,
            },
        )
        if not created and force:
            attend_member.server = server

        attend_member.save(
            update_fields=[
                "server",
            ]
        )
        return attend_member, created

    def remove_member_attendance(self, member: discord.Member) -> bool:
        try:
            attend_member = EventAttendance.objects.get(event=self, member_id=member.id)
            attend_member.delete()
        except EventAttendance.DoesNotExist:
            ...
        except EventAttendance.MultipleObjectsReturned:
            EventAttendance.objects.filter(event=self, member_id=member.id).delete()
        self._member_attendances.pop(member.id, None)
        return True

    async def do_finish(self) -> None:
        self.status = EventStatus.FINISHED
        self.save()

    async def do_cancel(self) -> None:
        self.status = EventStatus.CANCELED
        self.save()

    async def clean_reactions(self) -> None:
        message = await self.fetch_message()
        await message.clear_reactions()


class EventButtonsPersistentView(discord.ui.View):
    def __init__(self, cog: "BaseEventCog"):
        super().__init__(timeout=None)
        self.cog: "BaseEventCog" = cog
        self.event: t.Optional[EventItem] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        self.event = await self.cog.get_event_for_message(interaction.message.id)

        if not self.cog.is_event_moderator(self.event.guild_id, interaction.user.id):
            await interaction.response.send_message(
                ":face_with_symbols_over_mouth: "
                "Убрал руки! Это только для модераторов.",
                ephemeral=True,
            )
            return False

        if self.event.status in [EventStatus.FINISHED, EventStatus.CANCELED]:
            embed = event_embed(event=self.event)
            await interaction.response.edit_message(
                content=None, embed=embed, view=None
            )
            await self.event.clean_reactions()
            await interaction.followup.send(
                f":face_with_spiral_eyes: "
                f"Упс! Событие уже {self.event.get_status_display()}",
                ephemeral=True,
            )
            return False

        return True

    @discord.ui.button(
        label="Завершить",
        style=discord.ButtonStyle.green,
        custom_id="EVENT_BUTTON_PERSISTENT_VIEW:SUCCESS",
    )
    async def success(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self.event.do_finish()
        embed = event_embed(event=self.event)
        await interaction.response.edit_message(content=None, embed=embed, view=None)
        await self.event.clean_reactions()
        return

    @discord.ui.button(
        label="Отменить",
        style=discord.ButtonStyle.red,
        custom_id="EVENT_BUTTON_PERSISTENT_VIEW:CANCEL",
    )
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.event.do_cancel()
        embed = event_embed(event=self.event)
        await interaction.response.edit_message(content=None, embed=embed, view=None)
        await self.event.clean_reactions()


class BaseEventCog(commands.Cog):
    def __init__(self, bot: EveBot):
        self.bot: EveBot = bot

        self.bot.add_view(EventButtonsPersistentView(cog=self))

        self.event_class = EventItem
        self.event_class.bot = bot
        self.event_class.cog = self

        self._event_message_cache: dict[int, discord.Message] = {}
        self.cleanup_event_message_cache.start()
        self._event_moderators_cache: dict[int, dict] = {}
        self.cleanup_event_moderators_cache.start()

        self._event_channels_cache: dict[int, dict] = {}
        self.cleanup_event_channels_cache.start()

        try:
            self.ctx_menu_event_finish = app_commands.ContextMenu(
                name="Завершить событие", callback=self.context_event_finish
            )
            self.bot.tree.add_command(self.ctx_menu_event_finish)
        except CommandAlreadyRegistered:
            ...

    async def context_event_finish(
        self, interaction: discord.Interaction, message: discord.Message
    ):
        # We have to make sure the following query
        # takes <3s in order to meet the response window
        event = await self.get_event_for_message(message_id=message.id)
        if not event:
            await interaction.response.send_message(
                ":face_with_spiral_eyes: Упс! Тут нет события!", ephemeral=True
            )
            return False
        if event.status in [EventStatus.FINISHED, EventStatus.CANCELED]:
            await interaction.response.send_message(
                f":face_with_spiral_eyes: "
                f"Упс! Событие уже {event.get_status_display()}",
                ephemeral=True,
            )
            return False

        await interaction.response.send_modal(QuantityModal(cog=self, event=event))

    @tasks.loop(hours=1.0)
    async def cleanup_event_message_cache(self):
        self._event_message_cache.clear()

    @tasks.loop(hours=1.0)
    async def cleanup_event_moderators_cache(self):
        self._event_moderators_cache.clear()

    @tasks.loop(hours=1.0)
    async def cleanup_event_channels_cache(self):
        self._event_channels_cache.clear()

    @commands.Cog.listener()
    async def on_raw_reaction_add(
        self, payload: discord.RawReactionActionEvent
    ) -> None:
        # Проверим канал. Есть ли он в БД
        if not self.is_event_channel(
            guild_id=payload.guild_id, channel_id=payload.channel_id
        ):
            return

        message = await self.get_event_message(
            payload.channel_id, message_id=payload.message_id
        )
        event = await self.get_event_for_message(message_id=payload.message_id)

        member = payload.member

        # Сначала проверяем есть ли событие для этого сообщения
        if not event:
            await message.remove_reaction(payload.emoji, member)
            return

        if event.status == EventStatus.FINISHED:
            await message.remove_reaction(payload.emoji, member)
            return

        if member.bot:
            return

        if str(payload.emoji) in MemberReactions.emojis():
            current_member_attendance = MemberReactions(
                str(payload.emoji)
            ).attend_server
            old_member_attendance = event.member_attendance(member_id=member.id)
            if (
                old_member_attendance is not None
                and current_member_attendance != old_member_attendance
            ):
                emoji = MemberReactions(old_member_attendance).emoji
                await message.remove_reaction(emoji, member)

            event.add_member_attendance(member=member, server=current_member_attendance)
        else:
            await message.remove_reaction(str(payload.emoji), member)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(
        self, payload: discord.RawReactionActionEvent
    ) -> None:
        # message
        _ = await self.get_event_message(
            payload.channel_id, message_id=payload.message_id
        )
        event = await self.get_event_for_message(message_id=payload.message_id)

        # Сначала проверяем есть ли событие для этого сообщения
        if not event:
            return

        member = payload.member or event.guild.get_member(payload.user_id)

        if event.status == EventStatus.FINISHED:
            return

        if member.bot:
            return

        if str(payload.emoji) in MemberReactions.emojis():
            event.remove_member_attendance(member=member)

    async def cog_app_command_error(
        self, inter: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        logger.error(f'Error handled by "cog_app_command_error": {str(error)}')
        await inter.response.send_message(
            f"\N{SKULL AND CROSSBONES} Что-то пошло не так\n\n" f"> {str(error)}",
            ephemeral=True,
        )

    async def cog_command_error(self, ctx: EveContext, error: Exception) -> None:
        logger.error(f'Error handled by "cog_command_error": {str(error)}')
        await ctx.send(
            f"\N{SKULL AND CROSSBONES} " f"Что-то пошло не так\n\n" f"> {str(error)}",
            ephemeral=True,
        )

    def is_event_moderator(self, guild_id: int, member_id: int) -> bool:
        try:
            _ = self._event_moderators_cache[guild_id][member_id]
            return True
        except KeyError:
            try:
                _ = EventModerator.objects.get(guild_id=guild_id, member_id=member_id)
            except EventModerator.DoesNotExist:
                return False
            else:
                if guild_id not in self._event_moderators_cache:
                    self._event_moderators_cache[guild_id] = {}
                self._event_moderators_cache[guild_id].update({member_id: True})
                return True

    def is_event_channel(self, guild_id: int, channel_id: int) -> bool:
        try:
            _ = self._event_channels_cache[guild_id][channel_id]
            return True
        except KeyError:
            try:
                _ = EventChannel.objects.get(guild_id=guild_id, channel_id=channel_id)
            except EventChannel.DoesNotExist:
                return False
            else:
                if guild_id not in self._event_channels_cache:
                    self._event_channels_cache[guild_id] = {}
                self._event_channels_cache[guild_id].update({channel_id: True})
                return True

    async def get_event_message(
        self, channel_id: int, message_id: int
    ) -> t.Optional[discord.Message]:
        try:
            return self._event_message_cache[message_id]
        except KeyError:
            try:
                channel = self.bot.get_channel(channel_id)
                msg = await channel.fetch_message(message_id)
            except discord.HTTPException:
                return None
            else:
                self._event_message_cache[message_id] = msg
                return msg

    async def get_event_for_message(self, message_id: int) -> t.Optional[EventItem]:
        try:
            event = self.event_class.objects.get(message_id=message_id)
            return event
        except (EventItem.DoesNotExist, Event.DoesNotExist):
            return None
