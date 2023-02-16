from __future__ import annotations

import io
import logging
import discord
import platform
import re
import enum
import datetime
from enum_properties import EnumProperties, p, s
from typing import TYPE_CHECKING, Optional, List, Tuple, Union
from discord import app_commands
from discord.ext import commands, tasks
from evebot.utils.enums import EmojiEnumMIxin
from evebot.bot import EveBot, EveContext, GuildEveContext
from django.db import transaction
from activity.models import *
from activity.resources import CommonEventAttendanceResource
from evebot.utils import checks


if TYPE_CHECKING:
    ...


log = logging.getLogger(__name__)


# RESPAWN_RE = re.compile('\D+\s(\d{2}:\d{2}\*?|--:--)(\s+\d{2,3}%?)?', re.MULTILINE)
RESPAWN_RE = re.compile('\D+\s(\d{2}:\d{2}\*?|--:--)(\s+\d{2,3}%?)?(\s<-track)?', re.MULTILINE)


class MemberReactions(EmojiEnumMIxin, EnumProperties, s('emoji'), s('attend_type', case_fold=True)):
    FULL = enum.auto(), '✅', AttendanceType.FULL
    PARTIAL = enum.auto(), '⏲️', AttendanceType.PARTIAL


class ModeratorReactions(EmojiEnumMIxin, EnumProperties, s('emoji')):
    IS_MILITARY = enum.auto(), "⚔️"
    IS_OVERNIGHT = enum.auto(), "🌃"


class EventTemplateTransformer(app_commands.Transformer):
    async def transform(self, interaction: discord.Interaction, value: Union[str, int]) -> EventTemplate:
        event_template = EventTemplate.objects.get(id=int(value))
        return event_template


async def event_template_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    templates: List[EventTemplate] = list(EventTemplate.objects.all().order_by('id'))
    return [app_commands.Choice(name=f'{template.title} - '
                                     f'{template.cost} дкп за {template.capacity} {template.get_unit_display()}',
                                value=str(template.id))
            for template in templates if (current in template.title) or (current in template.description)]


def event_template_embed(template: EventTemplate) -> discord.Embed:
    embed = discord.Embed(colour=discord.Colour.blue())
    embed.title = f'{template.title}'
    embed.description = f'{template.description}'
    embed.add_field(name=f'Тип события', value=f'{template.get_type_display()}', inline=False)
    embed.add_field(name=f'Вознаграждение',
                    value=f'{template.cost} дкп '
                          f'за {template.capacity} / {template.get_unit_display()}', inline=False)
    embed.add_field(name=f'Опоздание', value=f'{template.penalty}% дкп', inline=True)
    embed.add_field(name=f'Наличие варов', value=f'+{template.military}% дкп', inline=True)
    embed.add_field(name=f'Ночь', value=f'+{template.overnight}% дкп', inline=True)
    return embed


def event_embed(event: EventItem) -> discord.Embed:
    colour = discord.Colour.light_gray()
    if event.status == EventStatus.STARTED:
        colour = discord.Colour.blue()
    elif event.status == EventStatus.CANCELED:
        colour = discord.Colour.red()
    elif event.status == EventStatus.FINISHED:
        colour = discord.Colour.green()

    embed = discord.Embed(colour=colour)

    embed.title = f'[СОБЫТИЕ] {event.title.upper()}'
    embed.description = f'{event.description or "..."}'

    embed.set_author(name=f'РЛ: {event.author.display_name}', icon_url=event.author.avatar.url)
    economy = f'ДКП:\t{event.cost}\n'
    if event.unit == CapacityUnit.TIME:
        economy += f'Расчетное время:\t{event.capacity} минут\n'
    elif event.unit == CapacityUnit.BOSS:
        economy += f'Расчетное количество:\t{event.capacity} боссов\n'
    elif event.unit == CapacityUnit.VISIT:
        economy += f'Расчетное количество:\t{event.capacity} посещений\n'

    if event.status == EventStatus.FINISHED:
        if event.unit == CapacityUnit.TIME:
            economy += f'Фактическое время:\t{event.quantity} минут\n'
        elif event.unit == CapacityUnit.VISIT:
            economy += f'Фактическое количество:\t{event.quantity} посещений\n'
        elif event.unit == CapacityUnit.BOSS:
            economy += f'Фактическое количество:\t{event.quantity} боссов\n'
        economy += f'**Присутствовавшие**: {event.full_reward} дкп\n' \
                   f'**Опоздавшие**: {event.partial_reward} дкп\n'

    embed.add_field(name=f'Бухгалтерия', value=economy, inline=False)

    embed.add_field(name=f'Номер события', value=f'{event.id}', inline=False)
    embed.add_field(name=f'Статус события', value=f'{event.get_status_display()}', inline=True)
    embed.add_field(name=f'Время события', value=f'{event.created.strftime("%d.%m.%Y %H:%M")}', inline=True)
    embed.add_field(name='', value='', inline=False)
    embed.add_field(name=f'Наличие варов', value=f'**{"Да" if event.is_military else "Нет"}**', inline=True)
    embed.add_field(name=f'Ночной', value=f'**{"Да" if event.is_overnight else "Нет"}**', inline=True)

    embed.add_field(name=f'Призыв', value=f'@everyone')

    embed.set_footer(text='✅    присутствовал\n'
                          '⏲️    опоздал\n'
                          '⚔️    вары (только для РЛ)\n'
                          '🌃    ночь (только для РЛ)')

    if event.status == EventStatus.FINISHED:
        guild_members = list([member for member in event.guild.members])

        full_attended_members = list(
            event.event_attendances.filter(type=AttendanceType.FULL).values_list('member_id', flat=True))
        partial_attended_members = list(
            event.event_attendances.filter(type=AttendanceType.PARTIAL).values_list('member_id', flat=True))

        full_filtered_members = list(filter(lambda member: member.id in full_attended_members, guild_members))
        partial_filtered_members = list(filter(lambda member: member.id in partial_attended_members, guild_members))

        full_attended = '\n'.join([member.mention for member in full_filtered_members])
        partial_attended = '\n'.join([member.mention for member in partial_filtered_members])
        embed.add_field(name=f'Присутствовавшие', value=f'{full_attended}', inline=True)
        embed.add_field(name=f'Опоздавшие', value=f'{partial_attended}', inline=True)

    return embed


class EventItem(Event):

    bot: Optional[EveBot] = None
    cog: Optional[EventCog] = None

    message: Optional[discord.Message]
    author: Optional[discord.Member]

    _member_attendances: dict[int, AttendanceType] = {}

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

    def set_is_military(self, value: bool):
        self.is_military = value
        self.save(update_fields=['is_military', ])

    def set_is_overnight(self, value: bool):
        self.is_overnight = value
        self.save(update_fields=['is_overnight', ])

    @property
    def do_ask_quantity(self):
        return self.quantity == 0

    @property
    def guild(self) -> Optional[discord.Guild]:
        if self.guild_id is not None:
            return self.bot.get_guild(self.guild_id)
        return None

    @property
    def channel(self) -> Optional[discord.TextChannel]:
        if self.channel_id is not None:
            return self.bot.get_channel(self.channel_id)
        return None

    @property
    def author(self) -> discord.Member:
        return self.guild.get_member(self.member_id)

    async def fetch_message(self) -> Optional[discord.Message]:
        channel = self.channel
        if channel is not None and self.message_id is not None:
            self.message = await self.cog.get_event_message(channel.id, self.message_id)
        return self.message

    @property
    def member_attendances(self) -> dict:
        # Подгружаем из БД то что есть ( при рестарте )
        if not self._member_attendances:
            members = self.event_attendances.all().values('member_id', 'type')
            for member in members:
                attend_type = AttendanceType(member['type'])
                self._member_attendances[member['member_id']] = attend_type
        return self._member_attendances

    def member_attendance(self, member_id: int):
        attend_type = self.member_attendances.get(member_id)
        return attend_type

    def add_member_attendance(self, member: discord.Member,
                              type: AttendanceType, force: bool = True) -> Tuple[EventAttendance, bool]:
        self._member_attendances[member.id] = type
        attend_member, created = EventAttendance.objects.get_or_create(
            event=self,
            member_id=member.id,
            defaults={
                'member_name': member.name,
                'member_display_name': member.display_name,
                'type': type
            }
        )
        if not created and force:
            attend_member.type = type

        attend_member.compute_reward(partial_save=False)
        attend_member.save(update_fields=['type', 'reward', ])
        return attend_member, created

    def remove_member_attendance(self, member: discord.Member) -> bool:
        try:
            attend_member = EventAttendance.objects.get(
                event=self,
                member_id=member.id
            )
            attend_member.delete()
        except EventAttendance.DoesNotExist:
            ...
        except EventAttendance.MultipleObjectsReturned:
            EventAttendance.objects.filter(
                event=self,
                member_id=member.id
            ).delete()
        self._member_attendances.pop(member.id, None)
        return True

    async def do_finish(self, quantity: int) -> None:

        self.quantity = quantity
        self.status = EventStatus.FINISHED
        self.save()

        attend_member, created = EventAttendance.objects.get_or_create(
            event=self,
            member_id=self.member_id,
            defaults={
                'member_name': self.member_name,
                'member_display_name': self.member_display_name,
                'type': AttendanceType.FULL
            }
        )
        if not created:
            attend_member.type = AttendanceType.FULL
            attend_member.compute_reward()
            attend_member.save(update_fields=['type', ])

        with transaction.atomic():
            for member_attendance in self.event_attendances.all():
                member_attendance.compute_reward()
                member_attendance.save()

    async def do_cancel(self) -> None:
        self.status = EventStatus.CANCELED
        self.save()

    async def clean_reactions(self) -> None:
        message = await self.fetch_message()
        await message.clear_reactions()


class QuantityModal(discord.ui.Modal):
    quantity = discord.ui.TextInput(label='Количество минут или количество боссов', placeholder='1',
                                    required=True, style=discord.TextStyle.short)

    def __init__(self, cog: EventCog, event: EventItem):
        self.cog = cog
        self.event = event
        super().__init__(title=f'{event.title} ({event.id})', timeout=None)

        if self.event.unit == CapacityUnit.TIME:
            self.quantity.label = f'Введите количество минут'
        elif self.event.unit == CapacityUnit.BOSS:
            self.quantity.label = f'Введите количество боссов'
        elif self.event.unit == CapacityUnit.VISIT:
            self.quantity.label = f'Введите количество посещений'

        self.quantity.placeholder = str(event.capacity)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        quantity = int(self.quantity.value)
        await self.event.do_finish(quantity=quantity)
        embed = event_embed(event=self.event)
        message = await self.event.fetch_message()
        await self.event.clean_reactions()
        await interaction.followup.edit_message(message_id=message.id, embed=embed, view=None)


class EventButtonsPersistentView(discord.ui.View):
    def __init__(self, cog: EventCog):
        super().__init__(timeout=None)
        self.cog: EventCog = cog
        self.event: Optional[EventItem] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        self.event = await self.cog.get_event_for_message(interaction.message.id)

        if not self.cog.is_event_moderator(self.event.guild_id, interaction.user.id):
            await interaction.response.send_message(
                f':face_with_symbols_over_mouth: Убрал руки! Это только для модераторов.', ephemeral=True)
            return False

        if self.event.status in [EventStatus.FINISHED, EventStatus.CANCELED]:
            embed = event_embed(event=self.event)
            await interaction.response.edit_message(content=None, embed=embed, view=None)
            await self.event.clean_reactions()
            await interaction.followup.send(
                f':face_with_spiral_eyes: Упс! Событие уже {self.event.get_status_display()}', ephemeral=True)
            return False

        return True

    @discord.ui.button(label='Завершить',
                       style=discord.ButtonStyle.green, custom_id='EVENT_BUTTON_PERSISTENT_VIEW:SUCCESS')
    async def success(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.event.do_ask_quantity:
            # SET QUANTITY BY DEFAULT (может быть никогда не сработает этот кейс)
            await self.event.do_finish(quantity=self.event.capacity)
            embed = event_embed(event=self.event)
            await interaction.response.edit_message(content=None, embed=embed, view=None)
            await self.event.clean_reactions()
            return

        await interaction.response.send_modal(QuantityModal(cog=self.cog, event=self.event))

    @discord.ui.button(label='Отменить',
                       style=discord.ButtonStyle.red, custom_id='EVENT_BUTTON_PERSISTENT_VIEW:CANCEL')
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.event.do_cancel()
        embed = event_embed(event=self.event)
        await interaction.response.edit_message(content=None, embed=embed, view=None)
        await self.event.clean_reactions()


class EventCog(commands.Cog):

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

        self.ctx_menu_event_finish = app_commands.ContextMenu(name='Завершить событие',
                                                              callback=self.context_event_finish)
        self.bot.tree.add_command(self.ctx_menu_event_finish)

    async def context_event_finish(self, interaction: discord.Interaction, message: discord.Message):
        # We have to make sure the following query takes <3s in order to meet the response window
        event = await self.get_event_for_message(message_id=message.id)
        if not event:
            await interaction.response.send_message(
                f':face_with_spiral_eyes: Упс! Тут нет события!', ephemeral=True)
            return False
        if event.status in [EventStatus.FINISHED, EventStatus.CANCELED]:
            await interaction.response.send_message(
                f':face_with_spiral_eyes: Упс! Событие уже {event.get_status_display()}', ephemeral=True)
            return False

        await interaction.response.send_modal(QuantityModal(cog=self, event=event))

    @tasks.loop(hours=1.0)
    async def cleanup_event_message_cache(self):
        self._event_message_cache.clear()

    @tasks.loop(hours=1.0)
    async def cleanup_event_moderators_cache(self):
        self._event_moderators_cache.clear()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        message = await self.get_event_message(payload.channel_id, message_id=payload.message_id)
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

        if str(payload.emoji) in ModeratorReactions.emojis():
            if not self.is_event_moderator(guild_id=payload.guild_id, member_id=member.id):
                await message.remove_reaction(payload.emoji, member)
                return

            react_flag = ModeratorReactions(str(payload.emoji))
            if react_flag == ModeratorReactions.IS_MILITARY:
                event.set_is_military(True)
            if react_flag == ModeratorReactions.IS_OVERNIGHT:
                event.set_is_overnight(True)
            return

        if str(payload.emoji) in MemberReactions.emojis():
            current_member_attendance = MemberReactions(str(payload.emoji)).attend_type
            old_member_attendance = event.member_attendance(member_id=member.id)
            if old_member_attendance is not None and current_member_attendance != old_member_attendance:
                emoji = MemberReactions(old_member_attendance).emoji
                await message.remove_reaction(emoji, member)

            event.add_member_attendance(member=member, type=current_member_attendance)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        message = await self.get_event_message(payload.channel_id, message_id=payload.message_id)
        event = await self.get_event_for_message(message_id=payload.message_id)
        member = payload.member or event.guild.get_member(payload.user_id)

        # Сначала проверяем есть ли событие для этого сообщения
        if not event:
            return

        if event.status == EventStatus.FINISHED:
            return

        if member.bot:
            return

        if str(payload.emoji) in ModeratorReactions.emojis():
            if not self.is_event_moderator(guild_id=payload.guild_id, member_id=member.id):
                return

            react_flag = ModeratorReactions(str(payload.emoji))
            if react_flag == ModeratorReactions.IS_MILITARY:
                event.set_is_military(False)
            if react_flag == ModeratorReactions.IS_OVERNIGHT:
                event.set_is_overnight(False)
            return

        if str(payload.emoji) in MemberReactions.emojis():
            event.remove_member_attendance(member=member)

    async def cog_app_command_error(self, inter: discord.Interaction,
                                    error: app_commands.AppCommandError) -> None:
        log.error(f'Error handled by "cog_app_command_error": {str(error)}')
        await inter.response.send_message(f'\N{SKULL AND CROSSBONES} Что-то пошло не так\n\n'
                                          f'> {str(error)}', ephemeral=True)

    async def cog_command_error(self, ctx: EveContext, error: Exception) -> None:
        log.error(f'Error handled by "cog_command_error": {str(error)}')
        await ctx.send(f'\N{SKULL AND CROSSBONES} Что-то пошло не так\n\n'
                       f'> {str(error)}', ephemeral=True)

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

    async def get_event_message(self, channel_id: int, message_id: int) -> Optional[discord.Message]:
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

    async def get_event_for_message(self, message_id: int) -> Optional[EventItem]:
        try:
            event = self.event_class.objects.get(message_id=message_id)
            return event
        except (EventItem.DoesNotExist, Event.DoesNotExist):
            return None

    @commands.hybrid_group(
        name='eventadmin',
        description='Группа команд для администрирования событий',
        with_app_command=True,
        invoke_without_command=False
    )
    @commands.is_owner()
    @commands.guild_only()
    @app_commands.guild_only()
    async def event_admin(self, ctx: GuildEveContext) -> None:
        ...

    @event_admin.group(
        name='channel',
        description='Добавление или удаление каналов для событий',
        with_app_command=True,
        invoke_without_command=False
    )
    @commands.is_owner()
    @commands.guild_only()
    @app_commands.guild_only()
    async def event_admin_channel(self, ctx: GuildEveContext) -> None:
        ...

    @event_admin.group(
        name='moderator',
        description='Добавление или удаление модераторов событий',
        with_app_command=True,
        invoke_without_command=False
    )
    @commands.is_owner()
    @commands.guild_only()
    @app_commands.guild_only()
    async def event_admin_moderator(self, ctx: GuildEveContext) -> None:
        ...

    @event_admin.group(
        name='template',
        description='Добавление или удаление шаблонов событий',
        with_app_command=True,
        invoke_without_command=False
    )
    @commands.is_owner()
    @commands.guild_only()
    @app_commands.guild_only()
    async def event_admin_template(self, ctx: GuildEveContext) -> None:
        ...

    @event_admin_channel.command(
        name='add',
        description='Добавление текстового канала для событий',
        with_app_command=True,
        invoke_without_command=False
    )
    @commands.is_owner()
    @commands.guild_only()
    @app_commands.guild_only()
    @app_commands.describe(channel='Текстовый канал для событий')
    async def event_admin_channel_add(self, ctx: GuildEveContext, channel: discord.TextChannel) -> None:
        event_channel, _ = EventChannel.objects.get_or_create(guild_id=ctx.guild.id, channel_id=channel.id)
        await ctx.send(f'Канал, {channel.mention}, настроен для использования событий!', reference=ctx.message)

    @event_admin_channel.command(
        name='del',
        description='Удаление текстового канала для событий',
        with_app_command=True,
        invoke_without_command=False
    )
    @commands.is_owner()
    @commands.guild_only()
    @app_commands.guild_only()
    @app_commands.describe(channel='Текстовый канал для событий')
    async def event_admin_channel_del(self, ctx: GuildEveContext, channel: discord.TextChannel) -> None:
        event_channel = EventChannel.objects.get(guild_id=ctx.guild.id, channel_id=channel.id)
        event_channel.delete()
        await ctx.send(f'Канал, {channel.mention}, больше не используется для событий!', reference=ctx.message)

    @event_admin_moderator.command(
        name='add',
        description='Добавление модератора событий',
        with_app_command=True,
        invoke_without_command=False
    )
    @commands.is_owner()
    @commands.guild_only()
    @app_commands.guild_only()
    @app_commands.describe(member='Участник, которому предоставить права модерации')
    async def event_admin_moderator_add(self, ctx: GuildEveContext, member: discord.Member) -> None:
        event_moderator, _ = EventModerator.objects.get_or_create(guild_id=ctx.guild.id, member_id=member.id)
        await ctx.send(f'Пользователь, {member.mention}, теперь является модератором!', reference=ctx.message)

    @event_admin_moderator.command(
        name='del',
        description='Удаление модератора событий',
        with_app_command=True,
        invoke_without_command=False
    )
    @commands.is_owner()
    @commands.guild_only()
    @app_commands.guild_only()
    @app_commands.describe(member='Участник, у которого отозвать права модератора')
    async def event_admin_moderator_del(self, ctx: GuildEveContext, member: discord.Member) -> None:
        event_moderator = EventModerator.objects.get(guild_id=ctx.guild.id, member_id=member.id)
        event_moderator.delete()
        await ctx.send(f'Пользователь, {member.mention}, теперь не является модератором!', reference=ctx.message)

    @event_admin_moderator.command(
        name='show',
        description='Показать всех модераторов',
        with_app_command=True,
        invoke_without_command=False
    )
    @commands.guild_only()
    @app_commands.guild_only()
    async def event_admin_moderator_show(self, ctx: GuildEveContext) -> None:
        event_moderators = EventModerator.objects.filter(guild_id=ctx.guild.id).values_list('member_id', flat=True)
        await ctx.send(f'Пока не работает :ghost:', reference=ctx.message)

    @event_admin_template.command(
        name='add',
        description='Добавление шаблона события',
        with_app_command=True,
        invoke_without_command=False
    )
    @commands.is_owner()
    @commands.guild_only()
    @app_commands.guild_only()
    @app_commands.describe(
        title='Отображаемое имя шаблона (32 символа)',
        description='Описание шаблона (255 символов)',
        type='Тип события',
        cost='Количество очков ДКП за объем участия (число больше 0)',
        capacity='Необходимый объем участия (число больше 0)',
        unit='Тип необходимого участия',
        penalty='Процент получаемый за опоздание (число от 0 до 100). По умолчанию 50',
        military='Процент надбавки при наличие варов (число от 0 до 100). По умолчанию 20',
        overnight='Процент надбавки за ночное время (число от 0 до 100). По умолчанию 25',
    )
    @app_commands.choices(
        type=[app_commands.Choice(name=label, value=value) for value, label in EventType.choices],
        unit=[app_commands.Choice(name=label, value=value) for value, label in CapacityUnit.choices],
    )
    async def event_admin_template_add(
            self,
            ctx: GuildEveContext,
            title: str,
            description: str,
            type: str,
            cost: int,
            capacity: int,
            unit: str,
            penalty: Optional[int] = 50,
            military: Optional[int] = 25,
            overnight: Optional[int] = 25
    ) -> None:
        template = EventTemplate.objects.create(
            title=title,
            description=description or '...',
            type=type,
            cost=cost,
            capacity=capacity,
            unit=unit,
            penalty=penalty,
            military=military,
            overnight=overnight
        )
        embed = event_template_embed(template=template)
        await ctx.send(embed=embed, reference=ctx.message)

    @event_admin_template.command(
        name='del',
        description='Удаление шаблона события',
        with_app_command=True,
        invoke_without_command=False
    )
    @commands.is_owner()
    @commands.guild_only()
    @app_commands.guild_only()
    @app_commands.describe(template='Шаблон события')
    @app_commands.autocomplete(template=event_template_autocomplete)
    async def event_admin_template_del(
            self,
            ctx: GuildEveContext,
            template: app_commands.Transform[EventTemplate, EventTemplateTransformer]) -> None:
        embed = event_template_embed(template=template)
        embed.colour = discord.Colour.red()
        embed.title = f'~~{embed.title}~~'
        embed.description = f'~~{embed.description}~~'
        template.delete()
        await ctx.send(embed=embed, reference=ctx.message)

    @commands.hybrid_group(
        name='eventmod',
        description='Группа команд для модерации событий',
        with_app_command=True,
        invoke_without_command=False
    )
    @commands.is_owner()
    @commands.guild_only()
    @app_commands.guild_only()
    async def event_mod(self, ctx: GuildEveContext) -> None:
        ...

    @event_mod.group(
        name='member',
        description='Добавление или удаление участника из события',
        with_app_command=True,
        invoke_without_command=False
    )
    @commands.guild_only()
    @app_commands.guild_only()
    @checks.event_channel_only()
    @checks.event_moderator_only()
    async def event_mod_member(self, ctx: GuildEveContext) -> None:
        ...

    @event_mod_member.command(
        name='add',
        description='Добавить участника к событию',
        with_app_command=True,
        invoke_without_command=False
    )
    @commands.guild_only()
    @app_commands.guild_only()
    @checks.event_channel_only()
    @checks.event_moderator_only()
    @app_commands.describe(
        member='Участник, которого надо добавить к событию',
        type='Тип присутствия на событии (присутствовал/опоздал/и тд)',
        event='Номер события'
    )
    @app_commands.choices(
        type=[app_commands.Choice(name=label, value=value) for value, label in AttendanceType.choices]
    )
    async def event_mod_member_add(self, ctx: GuildEveContext,
                               member: discord.Member, type: str, event: int) -> None:
        try:
            event = self.event_class.objects.get(id=event)
            event.add_member_attendance(member=member, type=type)

            event_message = await event.fetch_message()
            embed = event_embed(event=event)
            await event_message.edit(content=None, embed=embed, view=None)

            await ctx.send(f'{member.mention} '
                           f'добавлен к событию **{event.id}** '
                           f'как **{AttendanceType[type].label.upper()}**\n'
                           f'Событие: {event_message.jump_url}', reference=event_message)
        except (EventItem.DoesNotExist, Event.DoesNotExist):
            await ctx.send(f'\N{SKULL AND CROSSBONES} Событие с номером **{event}** не найдено.', ephemeral=True)

    @event_mod_member.command(
        name='del',
        description='Удалить участника из события',
        with_app_command=True,
        invoke_without_command=False
    )
    @commands.guild_only()
    @app_commands.guild_only()
    @checks.event_channel_only()
    @checks.event_moderator_only()
    @app_commands.describe(
        member='Участник, которого надо добавить к событию',
        event='Номер события'
    )
    async def event_mod_member_del(self, ctx: GuildEveContext, member: discord.Member, event: int) -> None:
        try:
            event = self.event_class.objects.get(id=event)
            event.remove_member_attendance(member=member)

            event_message = await event.fetch_message()
            embed = event_embed(event=event)
            await event_message.edit(content=None, embed=embed, view=None)

            await ctx.send(f'{member.mention} '
                           f'удален из события **{event.id}**\n'
                           f'Событие: {event_message.jump_url}', reference=event_message)
        except (EventItem.DoesNotExist, Event.DoesNotExist):
            await ctx.send(f'\N{SKULL AND CROSSBONES} Событие с номером **{event}** не найдено.', ephemeral=True)

    @event_mod.command(
        name='statistic',
        description='Статистика посещаемости',
        with_app_command=True,
        invoke_without_command=False
    )
    @commands.guild_only()
    @app_commands.guild_only()
    @checks.event_channel_only()
    @checks.event_moderator_only()
    @app_commands.describe(
        start='Пример: 2023-02-01 (YYYY-MM-DD)',
        end='Пример: 2023-02-09 (YYYY-MM-DD)',
        member='Участник, если надо получить индивидуальную статистику'
    )
    async def event_statistic(self, ctx: GuildEveContext,
                              start: str, end: str,
                              member: Optional[discord.Member]) -> None:

        start_date = datetime.datetime.strptime(start, "%Y-%m-%d")
        end_date = datetime.datetime.strptime(end, "%Y-%m-%d")

        filter = {
            'event__created__gte': start_date,
            'event__created__lte': end_date,
            'event__status': EventStatus.FINISHED
        }

        filename = f'report_{start}_{end}'
        if member:
            filter['member_id'] = member.id
            filename += f'_{member.name}'

        await ctx.defer(ephemeral=True)

        queryset = EventAttendance.objects.filter(**filter)
        resource = CommonEventAttendanceResource()
        result = resource.export(queryset=queryset)
        stat_data = io.BytesIO(result.xlsx)
        stat_file = discord.File(stat_data, filename=f'{filename}.xlsx',
                                 description=f'Статистика за период с {start_date} по {end_date}')

        await ctx.send(f'Все готово!', file=stat_file, ephemeral=True)

    @commands.hybrid_group(
        name='event',
        description='Группа команд для управления событиями',
        with_app_command=True,
        invoke_without_command=False
    )
    @commands.guild_only()
    @app_commands.guild_only()
    @checks.event_channel_only()
    @checks.event_moderator_only()
    async def event(self, ctx: GuildEveContext) -> None:
        ...

    @event.command(
        name='start',
        description='Запуск события по шаблону',
        with_app_command=True,
        invoke_without_command=False
    )
    @commands.guild_only()
    @app_commands.guild_only()
    @checks.event_channel_only()
    @checks.event_moderator_only()
    @app_commands.describe(template='Шаблон события',
                           description='Описание события или список респов')
    @app_commands.autocomplete(template=event_template_autocomplete)
    async def event_start(self, ctx: GuildEveContext,
                          template: app_commands.Transform[EventTemplate, EventTemplateTransformer],
                          description: Optional[str]) -> None:
        if description:
            respawn = '\n'.join([str(match.group()).rstrip().lstrip()
                                 for _, match in enumerate(RESPAWN_RE.finditer(description))])
            if respawn:
                description = f'**Список боссов**\n' \
                              f'```fix\n' \
                              f'{respawn}```'

        event = self.event_class.objects.create(
            guild_id=ctx.guild.id,
            channel_id=ctx.channel.id,
            member_id=ctx.author.id,
            member_name=ctx.author.name,
            member_display_name=ctx.author.display_name,
            type=template.type,
            unit=template.unit,
            capacity=template.capacity,
            cost=template.cost,
            penalty=template.penalty,
            military=template.military,
            overnight=template.overnight,
            title=template.title,
            description=description or template.description,
            status=EventStatus.STARTED
        )

        embed = event_embed(event=event)
        event_buttons_view = EventButtonsPersistentView(cog=self)

        message = await ctx.send(embed=embed, view=event_buttons_view)

        event.save(message_id=message.id)
        for event_reaction in MemberReactions.emojis() + ModeratorReactions.emojis():
            await message.add_reaction(event_reaction)


async def setup(bot):
    await bot.add_cog(EventCog(bot))
