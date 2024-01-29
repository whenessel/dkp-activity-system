import logging
import typing as t

import discord
from discord import app_commands
from discord.ext import commands

from activity.models import EventChannel, EventModerator

from .base import BaseEventCog

if t.TYPE_CHECKING:
    from evebot.bot import EveBot
    from evebot.context import EveContext, GuildEveContext


logger = logging.getLogger(__name__)


class AdminEventCog(BaseEventCog):
    @commands.hybrid_group(
        name="eventadmin",
        description="Группа команд для администрирования событий",
        with_app_command=True,
        invoke_without_command=False,
    )
    @commands.is_owner()
    @commands.guild_only()
    @app_commands.guild_only()
    async def event_admin(self, ctx: "GuildEveContext") -> None:
        ...

    @event_admin.group(
        name="channel",
        description="Добавление или удаление каналов для событий",
        with_app_command=True,
        invoke_without_command=False,
    )
    @commands.is_owner()
    @commands.guild_only()
    @app_commands.guild_only()
    async def event_admin_channel(self, ctx: "GuildEveContext") -> None:
        ...

    @event_admin.group(
        name="moderator",
        description="Добавление или удаление модераторов событий",
        with_app_command=True,
        invoke_without_command=False,
    )
    @commands.is_owner()
    @commands.guild_only()
    @app_commands.guild_only()
    async def event_admin_moderator(self, ctx: "GuildEveContext") -> None:
        ...

    @event_admin_channel.command(
        name="add",
        description="Добавление текстового канала для событий",
        with_app_command=True,
        invoke_without_command=False,
    )
    @commands.is_owner()
    @commands.guild_only()
    @app_commands.guild_only()
    @app_commands.describe(channel="Текстовый канал для событий")
    async def event_admin_channel_add(
        self, ctx: "GuildEveContext", channel: discord.TextChannel
    ) -> None:
        event_channel, _ = EventChannel.objects.get_or_create(
            guild_id=ctx.guild.id, channel_id=channel.id
        )
        await ctx.send(
            f"Канал, {channel.mention}, настроен для использования событий!",
            reference=ctx.message,
        )

    @event_admin_channel.command(
        name="del",
        description="Удаление текстового канала для событий",
        with_app_command=True,
        invoke_without_command=False,
    )
    @commands.is_owner()
    @commands.guild_only()
    @app_commands.guild_only()
    @app_commands.describe(channel="Текстовый канал для событий")
    async def event_admin_channel_del(
        self, ctx: "GuildEveContext", channel: discord.TextChannel
    ) -> None:
        event_channel = EventChannel.objects.get(
            guild_id=ctx.guild.id, channel_id=channel.id
        )
        event_channel.delete()
        await ctx.send(
            f"Канал, {channel.mention}, больше не используется для событий!",
            reference=ctx.message,
        )

    @event_admin_moderator.command(
        name="add",
        description="Добавление модератора событий",
        with_app_command=True,
        invoke_without_command=False,
    )
    @commands.is_owner()
    @commands.guild_only()
    @app_commands.guild_only()
    @app_commands.describe(member="Участник, которому предоставить права модерации")
    async def event_admin_moderator_add(
        self, ctx: "GuildEveContext", member: discord.Member
    ) -> None:
        event_moderator, _ = EventModerator.objects.get_or_create(
            guild_id=ctx.guild.id, member_id=member.id
        )
        await ctx.send(
            f"Пользователь, {member.mention}, теперь является модератором!",
            reference=ctx.message,
        )

    @event_admin_moderator.command(
        name="del",
        description="Удаление модератора событий",
        with_app_command=True,
        invoke_without_command=False,
    )
    @commands.is_owner()
    @commands.guild_only()
    @app_commands.guild_only()
    @app_commands.describe(member="Участник, у которого отозвать права модератора")
    async def event_admin_moderator_del(
        self, ctx: "GuildEveContext", member: discord.Member
    ) -> None:
        event_moderator = EventModerator.objects.get(
            guild_id=ctx.guild.id, member_id=member.id
        )
        event_moderator.delete()
        await ctx.send(
            f"Пользователь, {member.mention}, теперь не является модератором!",
            reference=ctx.message,
        )

    @event_admin_moderator.command(
        name="show",
        description="Показать всех модераторов",
        with_app_command=True,
        invoke_without_command=False,
    )
    @commands.guild_only()
    @app_commands.guild_only()
    async def event_admin_moderator_show(self, ctx: "GuildEveContext") -> None:
        event_moderators = EventModerator.objects.filter(
            guild_id=ctx.guild.id
        ).values_list("member_id", flat=True)
        members = ctx.guild.members
        moderators = filter(lambda member: member.id in event_moderators, members)
        moderators = ", ".join([member.mention for member in moderators])
        await ctx.send(
            f"Наши любимчики :heart_exclamation:\n{moderators}",
            reference=ctx.message,
        )


async def setup(bot):
    await bot.add_cog(AdminEventCog(bot))
