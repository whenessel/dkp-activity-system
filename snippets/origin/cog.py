import asyncio
import datetime
from typing import Any, Optional, List, Union
import discord
from discord.ext import commands
from discord import app_commands
from discord.utils import MISSING
from evebot.bot import EveBot, EveContext
from django.db.models.base import ModelBase
from activity.models import *
from django.db.models.query import QuerySet

from evebot.utils import cache
from .checks import event_channel_only, event_moderator_only
from ..utils.transformers import EventTemplateTransformer


MEMBER_REACTIONS = {
    "✅": EventRewardType.FULL,
    "⏲️": EventRewardType.LATE
}

MEMBER_REACTIONS_REVERS = {
    EventRewardType.FULL.value: "✅",
    EventRewardType.LATE.value: "⏲️"
}

MODERATOR_REACTIONS = {
    "⚔️": "is_military",
    "🌃": "is_overnight"
}


class EventItem(Event):

    _bot: Optional[EveBot] = None

    _guild: Optional[discord.Guild] = None
    _channel: Optional[discord.TextChannel] = None
    _message: Optional[discord.Message] = None
    _member: Optional[discord.Member] = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def save(self, message_id=None, status=None,
             force_insert=False, force_update=False, using=None, update_fields=None):
        if message_id:
            self.message_id = message_id
        if status:
            self.status = status
        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

    class Meta:
        proxy = True

    @property
    def bot(self):
        return self._bot

    @bot.setter
    def bot(self, value: EveBot):
        self._bot = value

    @property
    def guild(self) -> discord.Guild:
        if self._guild is None:
            self._guild = self.bot.get_guild(self.guild_id)
        return self._guild

    @property
    def channel(self) -> discord.TextChannel:
        if self._channel is None:
            self._channel = await self.guild.fetch_channel(self.channel_id)
        return self._channel

    @property
    async def message(self) -> Optional[discord.Message]:
        if self.message_id and self._message is None:
            self._message = await self.channel.fetch_message(self.message_id)
        return self._message

    @property
    def member(self) -> discord.Member:
        if self._member is None:
            self._member = self.guild.get_member(self.member_id)
        return self._member

    @property
    def embed(self) -> discord.Embed:
        _extra = ['✖️', '✔️']

        embed = discord.Embed(colour=discord.Colour.purple())
        embed.set_author(name=f"РЛ: {self.member.display_name}", icon_url=self.member.avatar.url)
        embed.title = f"{self.title}"
        embed.description = f"{self.description}"

        # economy = f"ДКП:\t{self.cost}\n"
        # if self.unit == EventUnit.TIME:
        #     economy += f"Расчетное время:\t{self.capacity} минут\n"
        # if self.capacity_unit == GameEventCapacityUnit.VISIT:
        #     economy += f"Расчетное количество:\t{self.capacity} посещений\n"
        # if self.capacity_unit == GameEventCapacityUnit.THING:
        #     economy += f"Расчетное количество:\t{self.capacity} боссов\n"
        #
        # embed.insert_field_at(index=0, name=f"Бухгалтерия", value=economy, inline=False)
        embed.add_field(name=f"Номер события", value=f"{self.id}", inline=False)
        embed.add_field(name=f"Статус события", value=f"{self.status}", inline=True)
        embed.add_field(name=f"Время события", value=f"{self.created.strftime('%d.%m.%Y %H:%M')}", inline=True)
        embed.add_field(name=f"", value=f"", inline=False)
        embed.add_field(name=f"Наличие варов", value=f"{_extra[0]}", inline=True)
        embed.add_field(name=f"Ночной", value=f"{_extra[0]}", inline=True)
        embed.add_field(name=f"Призыв", value=f"@everyone")
        embed.set_footer(text="✅\tприсутствовал\n⏲\tопоздал\n⚔\t️вары (только для РЛ)\n🌃\tночь (только для РЛ)")

        return embed

    # async def finish(self):
    #     message = await self.message
    #     self.save(status=EventStatus.FINISHED)
    #
    # def is_member_reaction(self, emoji: Union[discord.Emoji, discord.PartialEmoji]):
    #     if emoji.name in self.MEMBER_REACTIONS:
    #         return True
    #     return False
    #
    # def is_moderator_reaction(self, emoji: Union[discord.Emoji, discord.PartialEmoji]):
    #     if emoji.name in self.MODERATOR_REACTIONS:
    #         return True
    #     return False
    #
    # def get_member_reaction(self, member: discord.Member):
    #     try:
    #         event_reward = self.event_rewards.get(member_id=member.id)
    #         member_reaction = self.MEMBER_REACTIONS_REVERS.get(event_reward.type, None)
    #         return member_reaction
    #     except EventReward.DoesNotExist:
    #         return None
    #
    # def add_member_reaction(self, member: discord.Member, emoji: Union[discord.Emoji, discord.PartialEmoji]):
    #     reward_type = self.MEMBER_REACTIONS.get(emoji.name)
    #     reward = self.event_rewards.create(
    #         member_id=member.id,
    #         member_name=member.name,
    #         member_display_name=member.display_name,
    #         type=reward_type
    #     )
    #
    # def remove_member_reaction(self, member: discord.Member):
    #     try:
    #         reward = self.event_rewards.get(member_id=member.id)
    #         reward.delete()
    #     except EventReward.DoesNotExist:
    #         ...


class EventCog(commands.Cog):

    def __init__(self, bot: EveBot):
        self.bot: EveBot = bot
        self.event_class = self.get_event_class()
        # self.ctx_menu = app_commands.ContextMenu(name="Close event", callback=self.event_close_context_menu)
        # self.bot.tree.add_command(self.ctx_menu)

    # async def cog_load(self) -> None:
    #     ...
    #
    # def cog_unload(self):
    #     self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)
    #
    # async def event_close_context_menu(self, interaction: discord.Interaction, message: discord.Message):
    #     await interaction.response.defer()
    #     event: EventItem = await self.get_event_for_message(message_id=message.id)
    #     await event.finish()
    #     # await message.edit(content=message.content, embed=event.embed)
    #     await interaction.followup.send(content=message.content, embed=event.embed)
    #     print("...")

    def get_event_class(self):
        event_class = EventItem
        event_class.bot = self.bot
        return event_class

    async def get_event_channels(self, guild_id: int) -> List[discord.TextChannel]:
        event_channels = []
        for event_channel in EventChannel.objects.filter(guild_id=guild_id):
            channel = self.bot.get_channel(event_channel.channel_id)
            event_channels.append(channel)
        return event_channels

    async def get_templates(self) -> List[EventTemplate]:
        event_templates = list(EventTemplate.objects.all())
        return event_templates

    async def get_event_for_message(self, message_id: int) -> Optional[EventItem]:
        try:
            event = self.event_class.objects.get(message_id=message_id)
        except EventItem.DoesNotExist:
            event = None
        return event

    async def get_message_for_event(self, event_id: int) -> Optional[discord.Message]:
        message = None
        try:
            event = EventItem.objects.get(id=event_id)
            message = event.message
        except EventItem.DoesNotExist:
            event = None
        return message

    async def event_template_autocomplete(self,
                                          interaction: discord.Interaction,
                                          current: str) -> List[app_commands.Choice[str]]:
        templates: List[EventTemplate] = await self.get_templates()
        return [app_commands.Choice(name=template.title, value=str(template.id))
                for template in templates if current in template.title]

    event = app_commands.Group(name="event", description="...")

    # @event.command(name="start", description="Запуск события по шаблону")
    # @app_commands.guild_only()
    # @event_channel_only()
    # @event_moderator_only()
    # @app_commands.describe(template="Шаблон с преднастройками события",
    #                        description="Описание события")
    # @app_commands.autocomplete(template=event_template_autocomplete)
    # async def event_start(self, interaction: discord.Interaction,
    #                       template: app_commands.Transform[EventTemplate, EventTemplateTransformer],
    #                       description: Optional[str]) -> None:
    #     event = self.event_class.objects.create(
    #         guild_id=interaction.guild.id,
    #         channel_id=interaction.channel.id,
    #         member_id=interaction.user.id,
    #         member_name=interaction.user.name,
    #         member_display_name=interaction.user.display_name,
    #         type=template.type,
    #         unit=template.unit,
    #         capacity=template.capacity,
    #         cost=template.cost,
    #         penalty=template.penalty,
    #         military=template.military,
    #         overnight=template.overnight,
    #         title=template.title,
    #         description=description or template.description,
    #         status=EventStatus.STARTED
    #     )
    #     message = await interaction.response.send_message(embed=event.embed)
    #     if not message:
    #         message = await interaction.original_response()
    #
    #     event.save(message_id=message.id)
    #
    #     for event_reaction in list(event.MEMBER_REACTIONS.keys()) + list(event.MODERATOR_REACTIONS.keys()):
    #         await message.add_reaction(event_reaction)

    @event.command(name="debug", description="Отладка реакций")
    @app_commands.guild_only()
    @event_channel_only()
    @event_moderator_only()
    async def event_debug(self, interaction: discord.Interaction) -> None:
        template = EventTemplate.objects.first()
        event = self.event_class.objects.create(
            guild_id=interaction.guild.id,
            channel_id=interaction.channel.id,
            member_id=interaction.user.id,
            member_name=interaction.user.name,
            member_display_name=interaction.user.display_name,
            type=template.type,
            unit=template.unit,
            capacity=template.capacity,
            cost=template.cost,
            penalty=template.penalty,
            military=template.military,
            overnight=template.overnight,
            title=f"DEBUG: {template.title}",
            description=f"DEBUG: {template.description}",
            status=EventStatus.STARTED
        )
        message = await interaction.response.send_message(embed=event.embed)
        if not message:
            message = await interaction.original_response()

        event.save(message_id=message.id)

        for event_reaction in list(MEMBER_REACTIONS.keys()) + list(MODERATOR_REACTIONS.keys()):
            await message.add_reaction(event_reaction)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        guild = self.bot.get_guild(payload.guild_id)
        channel = guild.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        member = payload.member or guild.get_member(payload.user_id)

        if guild is None:
            return

        event_channels = await self.get_event_channels(guild_id=guild.id)
        if channel not in event_channels:
            return

        if member.bot:
            return None

        event = await self.get_event_for_message(message_id=payload.message_id)
        if not event:
            await message.remove_reaction(payload.emoji, member)
            return

        is_member_reaction = event.is_member_reaction(emoji=payload.emoji)
        is_moderator_reaction = event.is_moderator_reaction(emoji=payload.emoji)

        # prev_member_reaction = event.get_member_reaction(member=member)
        #
        # if is_member_reaction and not prev_member_reaction:
        #     event.add_member_reaction(member=member, emoji=payload.emoji)
        # elif is_member_reaction and prev_member_reaction:  # Re-reacted
        #     event.remove_member_reaction(member=member)
        #     await message.remove_reaction(prev_member_reaction, member)
        #     event.add_member_reaction(member=member, emoji=payload.emoji)
        # elif not is_member_reaction:
        #     await message.remove_reaction(payload.emoji, member)

    # @commands.Cog.listener()
    # async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
    #     guild = self.bot.get_guild(payload.guild_id)
    #     channel = guild.get_channel(payload.channel_id)
    #     message = await channel.fetch_message(payload.message_id)
    #     member = payload.member or guild.get_member(payload.user_id)
    #
    #     if guild is None:
    #         return
    #
    #     event_channels = await self.get_event_channels(guild_id=guild.id)
    #     if channel not in event_channels:
    #         return
    #
    #     if member.bot:
    #         return None
    #
    #     event = await self.get_event_for_message(message_id=payload.message_id)
    #     if not event:
    #         await message.remove_reaction(payload.emoji, member)
    #         return
    #
    #     is_member_reaction = event.is_member_reaction(emoji=payload.emoji)
    #     is_moderator_reaction = event.is_moderator_reaction(emoji=payload.emoji)
    #
    #     # member_reaction = event.get_member_reaction(member=member)
    #     #
    #     # if is_member_reaction:
    #     #     # event.remove_member_reaction(member=member)
    #     #     await message.remove_reaction(payload.emoji, member)
