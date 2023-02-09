from __future__ import annotations

import io
from typing import Any, Optional, List, Union, Tuple
import datetime
import discord
from discord.ext import commands, tasks
from discord import app_commands
from evebot.bot import EveBot, EveContext
from evebot.exceptions import NotEventChannel, NotEventModerator
from activity.models import *
from activity.resources import *
from django.db import transaction
from django.conf import settings
from .enums import ModeratorReactions, MemberReactions
from .checks import event_channel_only, event_moderator_only
from ..utils.transformers import EventTemplateTransformer


async def event_template_autocomplete(
        interaction: discord.Interaction,
        current: str) -> List[app_commands.Choice[str]]:
    templates: List[EventTemplate] = list(EventTemplate.objects.all().order_by("id"))
    # results = fuzzy.finder(current, templates, key=lambda t: t.choice_text, raw=True)
    return [app_commands.Choice(name=template.title, value=str(template.id))
            for template in templates if (current in template.title) or (current in template.description)]


async def event_attendices_type_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> List[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=attend_type.label, value=str(attend_type.value))
        for attend_type in [AttendanceType.FULL, AttendanceType.PARTIAL]
        if current.lower() in attend_type.label.lower()
    ]


class QuantityModal(discord.ui.Modal):
    quantity = discord.ui.TextInput(label="Количество минут или количество боссов", placeholder="1",
                                    required=True, style=discord.TextStyle.short)

    def __init__(self, cog: EventCog, event: EventItem):
        self.cog = cog
        self.event = event
        super().__init__(title=f"{event.title}", timeout=None)

        if self.event.unit == CapacityUnit.TIME:
            self.quantity.label = f"Введите количество минут"
        elif self.event.unit == CapacityUnit.THING:
            self.quantity.label = f"Введите количество боссов"
        elif self.event.unit == CapacityUnit.VISIT:
            self.quantity.label = f"Введите количество посещений"

        self.quantity._value = str(self.event.capacity)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        quantity = int(self.quantity.value)
        await self.event.do_finish(quantity=quantity)
        embed = self.event.embed
        await interaction.response.edit_message(content=None, embed=embed, view=None)


class EventButtonPersistentView(discord.ui.View):
    def __init__(self, cog: EventCog):
        super().__init__(timeout=None)
        self.cog: EventCog = cog

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not self.cog.is_moderator(interaction.user.id):
            await interaction.response.send_message(f"Убрал руки! Это только для модераторов.", ephemeral=True)
            return False
        event: EventItem = await self.cog.get_event_for_message(interaction.message.id)
        if event.status in [EventStatus.FINISHED, EventStatus.CANCELED]:
            # await interaction.response.edit_message(content=None, embed=event.embed, view=None)
            await interaction.response.send_message(f"Упс! Событие уже {event.get_status_display()}", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Завершить",
                       style=discord.ButtonStyle.green, custom_id="EVENT_BUTTON_PERSISTENT_VIEW:SUCCESS")
    async def success(self, interaction: discord.Interaction, button: discord.ui.Button):
        event: EventItem = await self.cog.get_event_for_message(interaction.message.id)

        if event.quantity == 0:
            await interaction.response.send_modal(QuantityModal(cog=self.cog, event=event))
        else:
            await event.do_finish()
            embed = event.embed
            await interaction.response.edit_message(content=None, embed=embed, view=None)

    @discord.ui.button(label="Отменить",
                       style=discord.ButtonStyle.red, custom_id="EVENT_BUTTON_PERSISTENT_VIEW:CANCEL")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        event: EventItem = await self.cog.get_event_for_message(interaction.message.id)
        await event.do_cancel()
        embed = event.embed
        await interaction.response.edit_message(content=None, embed=embed, view=None)


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
        self.save(update_fields=["is_military", ])

    def set_is_overnight(self, value: bool):
        self.is_overnight = value
        self.save(update_fields=["is_overnight", ])

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
            self.message = await self.cog.get_message(channel.id, self.message_id)
        return self.message

    @property
    def embed(self) -> discord.Embed:
        colour = discord.Colour.light_gray()
        if self.status == EventStatus.STARTED:
            colour = discord.Colour.blue()
        elif self.status == EventStatus.CANCELED:
            colour = discord.Colour.red()
        elif self.status == EventStatus.FINISHED:
            colour = discord.Colour.green()

        embed = discord.Embed(colour=colour)
        embed.set_author(name=f"РЛ: {self.author.display_name}", icon_url=self.author.avatar.url)
        embed.title = f"[{str(self.get_status_display()).upper()}] {self.title}"
        embed.description = f"{self.description}"

        economy = f"ДКП:\t{self.cost}\n"
        if self.unit == CapacityUnit.TIME:
            economy += f"Расчетное время:\t{self.capacity} минут\n"
        if self.unit == CapacityUnit.THING:
            economy += f"Расчетное количество:\t{self.capacity} боссов\n"
        if self.unit == CapacityUnit.VISIT:
            economy += f"Расчетное количество:\t{self.capacity} посещений\n"
        if self.status == EventStatus.FINISHED:
            if self.unit == CapacityUnit.TIME:
                economy += f"Фактическое время:\t{self.quantity} минут\n"
            if self.unit == CapacityUnit.VISIT:
                economy += f"Фактическое количество:\t{self.quantity} посещений\n"
            if self.unit == CapacityUnit.THING:
                economy += f"Фактическое количество:\t{self.quantity} боссов\n"
            economy += f"**Присутствовавшие**: {self.full_reward} дкп\n" \
                       f"**Опоздавшие**: {self.partial_reward} дкп\n"

        embed.add_field(name=f"Бухгалтерия", value=economy, inline=False)

        embed.add_field(name=f"Номер события", value=f"{self.id}", inline=False)
        embed.add_field(name=f"Статус события", value=f"{self.status}", inline=True)
        embed.add_field(name=f"Время события", value=f"{self.created.strftime('%d.%m.%Y %H:%M')}", inline=True)
        embed.add_field(name=f"", value=f"", inline=False)

        embed.add_field(name=f"Наличие варов", value=f"**{'Да' if self.is_military else 'Нет'}**", inline=True)
        embed.add_field(name=f"Ночной", value=f"**{'Да' if self.is_overnight else 'Нет'}**", inline=True)

        embed.add_field(name=f"Призыв", value=f"@everyone")

        embed.set_footer(text="✅    присутствовал\n"
                              "⏲️    опоздал\n"
                              "⚔️    вары (только для РЛ)\n"
                              "🌃    ночь (только для РЛ)")
        "⏲️"
        if self.status == EventStatus.FINISHED:
            guild_members = list([member for member in self.guild.members])

            full_attended_members = list(self.event_attendances.filter(type=AttendanceType.FULL).values_list('member_id', flat=True))
            partial_attended_members = list(self.event_attendances.filter(type=AttendanceType.PARTIAL).values_list('member_id', flat=True))

            full_filtered_members = list(filter(lambda member: member.id in full_attended_members, guild_members))
            partial_filtered_members = list(filter(lambda member: member.id in partial_attended_members, guild_members))

            full_attended = '\n'.join([member.mention for member in full_filtered_members])
            partial_attended = '\n'.join([member.mention for member in partial_filtered_members])
            embed.add_field(name=f"Присутствовавшие", value=f"{full_attended}", inline=True)
            embed.add_field(name=f"Опоздавшие", value=f"{partial_attended}", inline=True)

        return embed

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

    def add_member_attendance(self, member: discord.Member, type: AttendanceType) -> Tuple[EventAttendance, bool]:
        self._member_attendances[member.id] = type
        attend_member, created = EventAttendance.objects.get_or_create(
            event=self,
            member_id=member.id,
            defaults={
                "member_name": member.name,
                "member_display_name": member.display_name,
                "type": type
            }
        )
        if not created:
            attend_member.type = type
            # attend_member.save(update_fields=["type", ])
        attend_member.compute_reward(partial_save=False)
        attend_member.save(update_fields=["type", "reward", ])
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

    async def do_finish(self, quantity: Optional[int] = None):

        if quantity is not None:
            self.quantity = quantity

        if quantity == 0:
            self.quantity = self.capacity

        self.status = EventStatus.FINISHED
        self.save()

        attend_member, created = EventAttendance.objects.get_or_create(
            event=self,
            member_id=self.member_id,
            defaults={
                "member_name": self.member_name,
                "member_display_name": self.member_display_name,
                "type": AttendanceType.FULL
            }
        )
        if not created:
            attend_member.type = AttendanceType.FULL
            attend_member.compute_reward()
            attend_member.save(update_fields=["type", ])

        with transaction.atomic():
            for member_attendance in self.event_attendances.all():
                member_attendance.compute_reward()
                member_attendance.save()

    async def do_cancel(self):
        self.status = EventStatus.CANCELED
        self.save()


class EventCog(commands.Cog):

    def __init__(self, bot: EveBot):
        self.bot: EveBot = bot

        self.bot.add_view(EventButtonPersistentView(cog=self))

        self.event_class = EventItem
        self.event_class.bot = bot
        self.event_class.cog = self

        self._message_cache: dict[int, discord.Message] = {}
        self.cleanup_message_cache.start()
        self._moderators_cache: dict[int, EventModerator] = {}
        self.cleanup_moderators_cache.start()

    @tasks.loop(hours=1.0)
    async def cleanup_message_cache(self):
        self._message_cache.clear()

    @tasks.loop(hours=1.0)
    async def cleanup_moderators_cache(self):
        self._message_cache.clear()

    def is_moderator(self, member_id: int) -> bool:
        try:
            _ = self._moderators_cache[member_id]
            return True
        except KeyError:
            try:
                moderator = EventModerator.objects.get(member_id=member_id)
            except EventModerator.DoesNotExist:
                return False
            else:
                self._moderators_cache[member_id] = moderator
                return True

    async def get_message(self, channel_id: int, message_id: int) -> Optional[discord.Message]:
        try:
            return self._message_cache[message_id]
        except KeyError:
            try:
                channel = self.bot.get_channel(channel_id)
                msg = await channel.fetch_message(message_id)
            except discord.HTTPException:
                return None
            else:
                self._message_cache[message_id] = msg
                return msg

    async def get_event_for_message(self, message_id: int) -> Optional[EventItem]:
        try:
            event = self.event_class.objects.get(message_id=message_id)
            return event
        except (EventItem.DoesNotExist, Event.DoesNotExist):
            return None

    event = app_commands.Group(name="event", description="...")

    @event.command(name="start", description="Запуск события по шаблону")
    @app_commands.guild_only()
    @event_channel_only()
    @event_moderator_only()
    @app_commands.describe(template="Шаблон с преднастройками события",
                           description="Описание события",
                           quantity="Указать количество минут или количество боссов. По умолчанию из шаблона.")
    @app_commands.autocomplete(template=event_template_autocomplete)
    async def event_start(self, interaction: discord.Interaction,
                          template: app_commands.Transform[EventTemplate, EventTemplateTransformer],
                          description: Optional[str], quantity: Optional[int]) -> None:
        if quantity is None:
            quantity = template.quantity

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
            quantity=quantity,
            penalty=template.penalty,
            military=template.military,
            overnight=template.overnight,
            title=template.title,
            description=description or template.description,
            status=EventStatus.STARTED
        )
        event_button_view = EventButtonPersistentView(cog=self)
        message = await interaction.response.send_message(embed=event.embed, view=event_button_view)
        if not message:
            message = await interaction.original_response()

        event.save(message_id=message.id)

        for event_reaction in MemberReactions.emojis() + ModeratorReactions.emojis():
            await message.add_reaction(event_reaction)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        message = await self.get_message(payload.channel_id, message_id=payload.message_id)
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
            if not self.is_moderator(member_id=member.id):
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
        message = await self.get_message(payload.channel_id, message_id=payload.message_id)
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
            if not self.is_moderator(member_id=member.id):
                return

            react_flag = ModeratorReactions(str(payload.emoji))
            if react_flag == ModeratorReactions.IS_MILITARY:
                event.set_is_military(False)
            if react_flag == ModeratorReactions.IS_OVERNIGHT:
                event.set_is_overnight(False)
            return

        if str(payload.emoji) in MemberReactions.emojis():
            event.remove_member_attendance(member=member)

    @event.command(name="add", description="Добавить опоздавшего")
    @app_commands.guild_only()
    @event_channel_only()
    @event_moderator_only()
    @app_commands.autocomplete(type=event_attendices_type_autocomplete)
    async def event_member_add(self, interaction: discord.Interaction, event: int, member: discord.Member, type: str) -> None:
        try:
            event = self.event_class.objects.get(id=event)
            event.add_member_attendance(member=member, type=type)
            await interaction.response.send_message(f"{member.display_name} "
                                                    f"добавлен к событию {event.id} "
                                                    f"как {AttendanceType[type].label}", ephemeral=True)
        except (EventItem.DoesNotExist, Event.DoesNotExist):
            await interaction.response.send_message(f"Событие с номером {event} не найдено.", ephemeral=True)

    @event.command(name="del", description="Удаление участника события")
    @app_commands.guild_only()
    @event_channel_only()
    @event_moderator_only()
    async def event_member_del(self, interaction: discord.Interaction, event: int, member: discord.Member) -> None:
        try:
            event = self.event_class.objects.get(id=event)
            event.remove_member_attendance(member=member)
            await interaction.response.send_message(f"{member.display_name} "
                                                    f"удален из события {event.id}", ephemeral=True)
        except (EventItem.DoesNotExist, Event.DoesNotExist):
            await interaction.response.send_message(f"Событие с номером {event} не найдено.", ephemeral=True)

    @event.command(name="statistic", description="Статистика посещаемости.")
    @app_commands.guild_only()
    @event_channel_only()
    @event_moderator_only()
    @app_commands.describe(
        start="Пример: 2023-02-01 (YYYY-MM-DD)",
        end="Пример: 2023-02-09 (YYYY-MM-DD)",
        member="Участник, если надо получить индивидуальную стату"
    )
    async def event_debug(self, interaction: discord.Interaction,
                          start: str, end: str,
                          member: Optional[discord.Member]) -> None:

        start_date = datetime.datetime.strptime(start, "%Y-%m-%d")
        end_date = datetime.datetime.strptime(end, "%Y-%m-%d")
        filter = {
            "event__created__gte": start_date,
            "event__created__lt": end_date,
            "event__status": EventStatus.FINISHED
        }

        filename = f"report_{start}_{end}"
        if member:
            filter["member_id"] = member.id
            filename += f"_{member.name}"

        await interaction.response.defer()
        queryset = EventAttendance.objects.filter(**filter)
        resource = CommonEventAttendanceResource()
        result = resource.export(queryset=queryset)
        stat_data = io.BytesIO(result.xlsx)
        stat_file = discord.File(stat_data, filename=f"{filename}.xlsx",
                                 description=f"Статистика за период с {start_date} по {end_date}")
        # await interaction.response.send_message(content=f"Все готово!", file=stat_file, ephemeral=True)
        await interaction.followup.send(content=f"Все готово!", file=stat_file, ephemeral=True)

    # @event.command(name="debug", description="Только для разработки!")
    # @app_commands.guild_only()
    # @event_channel_only()
    # @event_moderator_only()
    # @app_commands.describe(
    #     start="Пример: 2023-02-01 (YYYY-MM-DD)",
    #     end="Пример: 2023-02-09 (YYYY-MM-DD)",
    #     member="Участник, если надо получить индивидуальную стату"
    # )
    # async def event_debug(self, interaction: discord.Interaction,
    #                       start: str, end: str,
    #                       member: Optional[discord.Member]) -> None:
    #
    #     start_date = datetime.datetime.strptime(start, "%Y-%m-%d")
    #     end_date = datetime.datetime.strptime(end, "%Y-%m-%d")
    #     filter = {
    #         "event__created__gte": start_date,
    #         "event__created__lt": end_date,
    #         "event__status": EventStatus.FINISHED
    #     }
    #
    #     filename = f"report_{start}_{end}"
    #     if member:
    #         filter["member_id"] = member.id
    #         filename += f"_{member.display_name}"
    #
    #     queryset = EventAttendance.objects.filter(**filter)
    #
    #     resource = CommonEventAttendanceResource()
    #     result = resource.export(queryset=queryset)
    #     stat_data = io.BytesIO(result.xlsx)
    #     stat_file = discord.File(stat_data, filename=f"{filename}.xlsx",
    #                              description=f"Статистика за период с {start_date} по {end_date}")
    #     await interaction.response.send_message(content=f"Все готово!", file=stat_file, ephemeral=True)
