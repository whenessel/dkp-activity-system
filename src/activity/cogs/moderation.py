import datetime
import logging
import typing as t

import discord
from dateutil.parser import parse
from discord import app_commands
from discord.ext import commands

from activity.choices import AttendanceServer, EventStatus
from activity.models import Event
from evebot.utils import checks

from ..services import ActivityStatisticService
from .base import (
    BaseEventCog,
    EventButtonsPersistentView,
    EventItem,
    MemberReactions,
    event_embed,
)

if t.TYPE_CHECKING:
    from evebot.bot import EveBot
    from evebot.context import EveContext, GuildEveContext


logger = logging.getLogger(__name__)


class DateTransformer(app_commands.Transformer):
    async def transform(
        self, interaction: discord.Interaction, value: str
    ) -> datetime.datetime:
        date = parse(value)
        return date


class ModerEventCog(BaseEventCog):
    @commands.hybrid_group(
        name="eventmod",
        description="Группа команд для модерации событий",
        with_app_command=True,
        invoke_without_command=False,
    )
    @commands.is_owner()
    @commands.guild_only()
    @app_commands.guild_only()
    async def event_mod(self, ctx: "GuildEveContext") -> None:
        ...

    @event_mod.group(
        name="member",
        description="Добавление или удаление участника из события",
        with_app_command=True,
        invoke_without_command=False,
    )
    @commands.guild_only()
    @app_commands.guild_only()
    @checks.event_channel_only()
    @checks.event_moderator_only()
    async def event_mod_member(self, ctx: "GuildEveContext") -> None:
        ...

    @event_mod_member.command(
        name="add",
        description="Добавить участника к событию",
        with_app_command=True,
        invoke_without_command=False,
    )
    @commands.guild_only()
    @app_commands.guild_only()
    @checks.event_channel_only()
    @checks.event_moderator_only()
    @app_commands.describe(
        member="Участник, которого надо добавить к событию",
        server="Сервер участника",
        event="Номер события",
    )
    @app_commands.choices(
        server=[
            app_commands.Choice(name=label, value=value)
            for value, label in AttendanceServer.choices
        ]
    )
    async def event_mod_member_add(
        self, ctx: "GuildEveContext", member: discord.Member, server: str, event: int
    ) -> None:
        try:
            event = self.event_class.objects.get(id=event)
            event.add_member_attendance(member=member, server=server)

            event_message = await event.fetch_message()
            embed = event_embed(event=event)
            await event_message.edit(content=None, embed=embed, view=None)

            await ctx.send(
                f"Добавлен участник {member.mention} "
                f"к событию **{event.id} ({event.title})**\n"
                f"Перейти к событию: {event_message.jump_url}",
                reference=event_message,
            )
        except (EventItem.DoesNotExist, Event.DoesNotExist):
            await ctx.send(
                f"\N{SKULL AND CROSSBONES} "
                f"Событие с номером **{event}** не найдено.",
                ephemeral=True,
            )

    @event_mod_member.command(
        name="del",
        description="Удалить участника из события",
        with_app_command=True,
        invoke_without_command=False,
    )
    @commands.guild_only()
    @app_commands.guild_only()
    @checks.event_channel_only()
    @checks.event_moderator_only()
    @app_commands.describe(
        member="Участник, которого надо удалить из события", event="Номер события"
    )
    async def event_mod_member_del(
        self, ctx: "GuildEveContext", member: discord.Member, event: int
    ) -> None:
        try:
            event = self.event_class.objects.get(id=event)
            event.remove_member_attendance(member=member)

            event_message = await event.fetch_message()
            embed = event_embed(event=event)
            await event_message.edit(content=None, embed=embed, view=None)

            await ctx.send(
                f"Удален участник {member.mention} из события "
                f"**{event.id} ({event.title})**\n"
                f"Перейти к событию: {event_message.jump_url}",
                reference=event_message,
            )

        except (EventItem.DoesNotExist, Event.DoesNotExist):
            await ctx.send(
                f"\N{SKULL AND CROSSBONES} "
                f"Событие с номером **{event}** не найдено.",
                ephemeral=True,
            )

    @event_mod.command(
        name="sync",
        description="Синхронизация данных события с базой",
        with_app_command=True,
        invoke_without_command=False,
    )
    @commands.guild_only()
    @app_commands.guild_only()
    @checks.event_channel_only()
    @checks.event_moderator_only()
    async def event_sync(self, ctx: "GuildEveContext", event: int) -> None:
        try:
            event: EventItem = EventItem.objects.get(id=event)

            event_message = await event.fetch_message()
            embed = event_embed(event=event)

            await event_message.edit(content=None, embed=embed, view=None)

            await ctx.send(
                f"**Синхронизировано**\n"
                f"Событие: **{event.title}**\n"
                f"Перейти к событию: {event_message.jump_url}",
                reference=event_message,
                ephemeral=True,
            )

        except (EventItem.DoesNotExist, Event.DoesNotExist):
            await ctx.send(
                f"\N{SKULL AND CROSSBONES} Событие с номером **{event}** не найдено.",
                ephemeral=True,
            )

    @event_mod.command(
        name="delete",
        description="Удаление события",
        with_app_command=True,
        invoke_without_command=False,
    )
    @commands.guild_only()
    @app_commands.guild_only()
    @checks.event_channel_only()
    @checks.event_moderator_only()
    async def event_delete(self, ctx: "GuildEveContext", event: int) -> None:
        try:
            event: EventItem = EventItem.objects.get(id=event)
            event.status = EventStatus.DELETED
            event.save()

            event_message = await event.fetch_message()
            embed = event_embed(event=event)

            await event_message.edit(content=None, embed=embed, view=None)

            await ctx.send(
                f"**Удалено**\n"
                f"Событие: **{event.title}**\n"
                f"Перейти к событию: {event_message.jump_url}",
                reference=event_message,
                ephemeral=True,
            )

        except (EventItem.DoesNotExist, Event.DoesNotExist):
            await ctx.send(
                f"\N{SKULL AND CROSSBONES} "
                f"Событие с номером **{event}** не найдено.",
                ephemeral=True,
            )

    @commands.hybrid_group(
        name="event",
        description="Группа команд для управления событиями",
        with_app_command=True,
        invoke_without_command=False,
    )
    @commands.guild_only()
    @app_commands.guild_only()
    @checks.event_channel_only()
    @checks.event_moderator_only()
    async def event(self, ctx: "GuildEveContext") -> None:
        ...

    @event.command(
        name="start",
        description="Запуск события",
        with_app_command=True,
        invoke_without_command=False,
    )
    @commands.guild_only()
    @app_commands.guild_only()
    @checks.event_channel_only()
    @checks.event_moderator_only()
    @app_commands.describe(
        title='Название события. По умолчанию "Сбор Арена"',
        schedule="Запланированное время сбора. Формат: 14:00",
    )
    async def event_start(
        self, ctx: "GuildEveContext", title: t.Optional[str], schedule: str
    ) -> None:
        if not title:
            title = "Сбор Арена"

        event = self.event_class.objects.create(
            guild_id=ctx.guild.id,
            channel_id=ctx.channel.id,
            member_id=ctx.author.id,
            member_name=ctx.author.name,
            member_display_name=ctx.author.display_name,
            title=title,
            description=schedule,
            status=EventStatus.STARTED,
        )

        embed = event_embed(event=event)
        event_buttons_view = EventButtonsPersistentView(cog=self)

        message = await ctx.send(embed=embed, view=event_buttons_view)

        event.save(message_id=message.id)
        for event_reaction in MemberReactions.emojis():
            await message.add_reaction(event_reaction)

    @commands.hybrid_group(
        name="eventstats",
        description="Группа команд для статистики событий",
        with_app_command=True,
        invoke_without_command=False,
    )
    @commands.is_owner()
    @commands.guild_only()
    @app_commands.guild_only()
    @checks.event_channel_only()
    @checks.event_moderator_only()
    async def event_stats(self, ctx: "GuildEveContext") -> None:
        ...

    @event_stats.command(
        name="daterange",
        description="Статистика посещаемости за выбранный диапазон дат",
        with_app_command=True,
        invoke_without_command=False,
    )
    @commands.guild_only()
    @app_commands.guild_only()
    @checks.event_channel_only()
    @checks.event_moderator_only()
    @app_commands.describe(
        start_date="Дата начала статистики. Форматы: 2024-01-01|2024-1-1|2024/1/1",
        end_date="Дата начала статистики. Форматы: 2024-01-01|2024-1-1|2024/1/1",
    )
    async def event_stats_date_range(
        self,
        ctx: "GuildEveContext",
        start_date: app_commands.Transform[datetime.datetime, DateTransformer],
        end_date: app_commands.Transform[datetime.datetime, DateTransformer],
    ) -> None:
        await ctx.defer(ephemeral=True)

        statistic_service = ActivityStatisticService()
        statistic_file = statistic_service.get_statistics_by_date_range(
            start_date=start_date, end_date=end_date
        )
        await ctx.send("Все готово!", file=statistic_file, ephemeral=True)

    @event_stats.command(
        name="eventrange",
        description="Статистика посещаемости за выбранный диапазон событий",
        with_app_command=True,
        invoke_without_command=False,
    )
    @commands.guild_only()
    @app_commands.guild_only()
    @checks.event_channel_only()
    @checks.event_moderator_only()
    @app_commands.describe(
        start_id="ID события начала статистики.",
        end_id="ID события конца статистики.",
    )
    async def event_stats_event_range(
        self,
        ctx: "GuildEveContext",
        start_id: int,
        end_id: int,
    ) -> None:
        await ctx.defer(ephemeral=True)

        statistic_service = ActivityStatisticService()
        statistic_file = statistic_service.get_statistics_by_event_range(
            start_id=start_id, end_id=end_id
        )
        await ctx.send("Все готово!", file=statistic_file, ephemeral=True)

    @event_stats.command(
        name="events",
        description="Статистика посещаемости за выбранные события",
        with_app_command=True,
        invoke_without_command=False,
    )
    @commands.guild_only()
    @app_commands.guild_only()
    @checks.event_channel_only()
    @checks.event_moderator_only()
    @app_commands.describe(
        event_ids="Список событий для статистики. "
        "Одно или более значений через пробел",
    )
    async def event_stats_event_list(
        self,
        ctx: "GuildEveContext",
        event_ids: commands.Greedy[int],
    ) -> None:
        await ctx.defer(ephemeral=True)

        statistic_service = ActivityStatisticService()
        statistic_file = statistic_service.get_statistics_by_event_list(
            event_ids=event_ids
        )
        await ctx.send("Все готово!", file=statistic_file, ephemeral=True)


async def setup(bot):
    await bot.add_cog(ModerEventCog(bot))
