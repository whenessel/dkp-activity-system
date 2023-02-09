from __future__ import annotations
import discord
import platform
from typing import Optional, List
from discord import app_commands
from discord.ext import commands
from discord.utils import MISSING
from evebot.bot import EveBot, EveContext
from evebot.utils import fuzzy
from .utils.transformers import EventTemplateTransformer
from ..models import *


async def event_unit_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=unit_label, value=unit_value)
        for unit_value, unit_label in CapacityUnit.choices if current.lower() in unit_label.lower()
    ]


async def event_type_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=type_label, value=type_value)
        for type_value, type_label in EventType.choices if current.lower() in type_label.lower()
    ]


async def event_template_autocomplete(
        interaction: discord.Interaction,
        current: str) -> List[app_commands.Choice[str]]:
    templates: List[EventTemplate] = list(EventTemplate.objects.all())
    # results = fuzzy.finder(current, templates, key=lambda t: t.choice_text, raw=True)
    return [app_commands.Choice(name=template.title, value=str(template.id))
            for template in templates if (current in template.title) or (current in template.description)]


def event_template_embed(template: EventTemplate) -> discord.Embed:
    embed = discord.Embed(colour=discord.Colour.blue())
    embed.title = f"{template.title}"
    embed.description = f"{template.description}"
    embed.add_field(name=f"Тип события", value=f"{template.get_type_display()}", inline=False)
    embed.add_field(name=f"Вознаграждение",
                    value=f"{template.cost} дкп "
                          f"за {template.capacity} / {template.get_unit_display()}", inline=False)
    embed.add_field(name=f"Опоздание", value=f"-{template.penalty}%", inline=True)
    embed.add_field(name=f"Наличие варов", value=f"+{template.military}%", inline=True)
    embed.add_field(name=f"Ночь", value=f"+{template.overnight}%", inline=True)
    return embed


class General(commands.Cog):

    def __init__(self, bot):
        self.bot: EveBot = bot

    eventadmin = app_commands.Group(name="eventadmin", description="...")
    eventadmin_channel = app_commands.Group(name="channel", description="...", parent=eventadmin)
    eventadmin_moderator = app_commands.Group(name="moderator", description="...", parent=eventadmin)
    eventadmin_template = app_commands.Group(name="template", description="...", parent=eventadmin)

    @eventadmin_channel.command(
        name="add",
        description="Добавление текстового канала для событий"
    )
    @app_commands.guild_only()
    @commands.is_owner()
    async def eventadmin_channel_add(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        event_channel, created = EventChannel.objects.get_or_create(guild_id=interaction.guild.id, channel_id=channel.id)
        channel = self.bot.get_channel(event_channel.channel_id)
        if created:
            await interaction.response.send_message(
                f"Отлично! Теперь, {channel.mention}, будет использоваться для работы с событиями!"
            )
        else:
            await interaction.response.send_message(
                f"Упс! {channel.mention}, уже используется!"
            )

    @eventadmin_channel.command(
        name="del",
        description="Удаление текстового канала для событий"
    )
    @app_commands.guild_only()
    @commands.is_owner()
    async def eventadmin_channel_del(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        try:
            event_channel = EventChannel.objects.get(guild_id=interaction.guild.id, channel_id=channel.id)
            event_channel.delete()
            await interaction.response.send_message(
                f"Теперь, {channel.mention} не используется для событий!"
            )
        except EventChannel.DoesNotExist:
            await interaction.response.send_message(
                f"Упс! {channel.mention} не используется для событий!"
            )

    @eventadmin_moderator.command(
        name="add",
        description="Добавление прав модератора событий участнику"
    )
    @app_commands.guild_only()
    @commands.is_owner()
    async def eventadmin_moderator_add(self, interaction: discord.Interaction, member: discord.Member) -> None:
        event_moderator, created = EventModerator.objects.get_or_create(guild_id=interaction.guild.id,
                                                                        member_id=member.id)
        if created:
            await interaction.response.send_message(
                f"Отлично! Теперь, {member.mention}, является модератором событий!"
            )
        else:
            await interaction.response.send_message(
                f"Упс! {member.mention}, уже модератор!"
            )

    @eventadmin_moderator.command(
        name="del",
        description="Удаление прав модератора событий у участника"
    )
    @app_commands.guild_only()
    @commands.is_owner()
    async def eventadmin_moderator_del(self, interaction: discord.Interaction, member: discord.Member) -> None:
        try:
            event_moderator = EventModerator.objects.get(guild_id=interaction.guild.id, member_id=member.id)
            event_moderator.delete()
            await interaction.response.send_message(
                f"Теперь, {member.mention}, не является модератором событий!"
            )
        except EventChannel.DoesNotExist:
            await interaction.response.send_message(
                f"Упс! {member.mention}, не модератор событий!"
            )

    @eventadmin_template.command(
        name="add",
        description="Добавление шаблона события"
    )
    @app_commands.guild_only()
    @commands.is_owner()
    @app_commands.describe(
        title="Отображаемое имя шаблона (32 символа)",
        description="Описание шаблона (255 символов)",
        type="Тип события (полный список будет позже)",
        cost="Количество очков ДКП за объем участия (число больше 0)",
        capacity="Необходимый объем участия (число больше 0)",
        unit="Тип необходимого участия",
        quantity="Количество по умолчанию. По умолчанию равно CAPACITY (можно изменить при создании)",
        penalty="Процент получаемый за опоздание (число от 0 до 100). По умолчанию 50",
        military="Процент надбавки при наличие варов (число от 0 до 100). По умолчанию 20",
        overnight="Процент надбавки за ночное время (число от 0 до 100). По умолчанию 25",
    )
    @app_commands.autocomplete(type=event_type_autocomplete, unit=event_unit_autocomplete)
    async def eventadmin_template_add(
            self,
            interaction: discord.Interaction,
            title: str,
            description: str,
            type: str,
            cost: int,
            capacity: int,
            unit: str,
            quantity: Optional[int],
            penalty: Optional[int] = 50,
            military: Optional[int] = 25,
            overnight: Optional[int] = 25,
    ) -> None:
        if quantity is None:
            quantity = capacity

        event_template = EventTemplate.objects.create(
            title=title,
            description=description,
            type=type,
            cost=cost,
            capacity=capacity,
            unit=unit,
            quantity=quantity,
            penalty=penalty,
            military=military,
            overnight=overnight
        )
        embed = event_template_embed(template=event_template)
        await interaction.response.send_message(embed=embed)

    @eventadmin_template.command(
        name="del",
        description="Удаление шаблона события"
    )
    @app_commands.guild_only()
    @commands.is_owner()
    @app_commands.autocomplete(template=event_template_autocomplete)
    async def eventadmin_template_del(self, interaction: discord.Interaction,
                                      template: app_commands.Transform[EventTemplate, EventTemplateTransformer]
                                      ) -> None:

        embed = event_template_embed(template=template)
        embed.colour=discord.Colour.red()
        embed.title = f"[Удалено] {embed.title}"
        template.delete()
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(General(bot))
