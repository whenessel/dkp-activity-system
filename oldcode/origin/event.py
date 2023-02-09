import asyncio
import datetime
from typing import Dict, Optional, List, Any
from typing import Callable, TypeVar

import discord
from discord import app_commands, MessageType
from discord.ext import commands
from discord.ext.commands import Context
from discord.ext.commands._types import BotT, Check

from evebot.bot import EveBot, EveContext
from evebot.utils import fuzzy, cache
from evebot.utils.strings import get_shortened_string
from ..models import *


T = TypeVar('T')


class NotActivityChannel(commands.CheckFailure):
    """
    Thrown when a user is attempting something into not configured ActivityChannel.
    """

    def __init__(self, message: Optional[str] = None):
        super().__init__(message or 'This command cannot be used in this TextChannel.')


def is_activity_channel():
    async def predicate(ctx: EveContext) -> bool:
        activity_channels = ActivityChannel.objects.filter(guild_id=ctx.guild.id, channel_id=ctx.channel.id)

        if not activity_channels.exists():
            raise NotActivityChannel

        return True

    return commands.check(predicate)


# class GameEventService:
#
#     USER_REACTIONS = {
#         '✅': GameEventUserState.FULL,
#         '⏲️': GameEventUserState.LATE
#     }
#
#     LEADER_REACTIONS = {
#         '⚔️': True,
#         '🌃': True
#     }
#
#     active_events: Dict[int, GameEvent] = {}
#     active_event_reactions: Dict[int, Dict[discord.User, Optional[discord.Reaction]]] = {}
#
#     def __init__(self):
#         ...
#
#     def get_templates(self) -> list[GameEventTemplate]:
#         return list([event_template for event_template in GameEventTemplate.objects.all()])
#
#     def get_template(self, template_id: int) -> GameEventTemplate:
#         return GameEventTemplate.objects.get(id=template_id)
#
#     def add_active_event(self, message: discord.Message, author: discord.User, template: GameEventTemplate) -> GameEvent:
#         event = GameEvent(
#             guild_id=message.guild.id,
#             channel_id=message.channel.id,
#             message_id=message.id,
#             author_id=author.id,
#             author_name=author.name,
#             author_display_name=author.display_name,
#             state=GameEventState.STARTED,
#             title=template.title,
#             description=template.description,
#             event_type=template.event_type,
#             cost=template.cost,
#             capacity=template.capacity,
#             capacity_unit=template.capacity_unit,
#             lateness_percent=template.lateness_percent,
#             nightly_percent=template.nightly_percent,
#             quantity=None,
#             created=datetime.datetime.now()
#         )
#
#         if event.event_type == GameEventType.CHAIN and event.capacity_unit == GameEventCapacityUnit.MINUTE:
#             event.quantity = None
#         elif event.event_type == GameEventType.CHAIN and event.capacity_unit == GameEventCapacityUnit.THING:
#             event.quantity = None
#         else:
#             event.quantity = template.capacity
#
#         self.active_events[message.id] = event
#         self.active_event_reactions[message.id] = {}
#
#         return event
#
#     def get_active_event(self, message: discord.Message):
#         return self.active_events.get(message.id)
#
#     def set_quantity_event(self, message: discord.Message, quantity: int):
#         event = self.active_events.get(message.id)
#         event.quantity = quantity
#
#     def check_leader_reaction(self, reaction: discord.Reaction) -> bool:
#         if reaction.emoji in self.LEADER_REACTIONS:
#             return True
#         return False
#
#     def check_user_reaction(self, reaction: discord.Reaction) -> bool:
#         if reaction.emoji in self.USER_REACTIONS:
#             return True
#         return False
#
#     def check_user_reacted(self, message: discord.Message, user: [discord.User, discord.Member]) -> [discord.Reaction, None]:
#         data = self.active_event_reactions[message.id]
#         user_reaction = data.get(user)
#         return user_reaction
#
#     def add_reaction(self, message: discord.Message, user: [discord.User, discord.Member], reaction: discord.Reaction) -> None:
#         data = self.active_event_reactions[message.id]
#         data[user] = reaction
#
#     def remove_reaction(self, message: discord.Message, user: [discord.User, discord.Member]) -> None:
#         data = self.active_event_reactions[message.id]
#         data[user] = None
#
#     def _make_embed(self, ctx: Context, message: discord.Message):
#         _extra = ['✖️', '✔️']
#
#         event = self.get_active_event(message=message)
#         embed = discord.Embed(colour=discord.Colour.dark_gray())
#         embed.set_author(name=f"РЛ: {event.author_display_name}", icon_url=ctx.author.avatar.url)
#         embed.title = f"{event.title}"
#         embed.description = f"{event.description}"
#
#         economy = f"ДКП:\t{event.cost}\n"
#         if event.capacity_unit == GameEventCapacityUnit.MINUTE:
#             economy += f"Расчетное время:\t{event.capacity} минут\n"
#         if event.capacity_unit == GameEventCapacityUnit.VISIT:
#             economy += f"Расчетное количество:\t{event.capacity} посещений\n"
#         if event.capacity_unit == GameEventCapacityUnit.THING:
#             economy += f"Расчетное количество:\t{event.capacity} боссов\n"
#
#         embed.insert_field_at(index=0, name=f"Бухгалтерия", value=economy, inline=False)
#
#         embed.add_field(name=f"Номер события", value=f"{event.message_id}", inline=False)
#         embed.add_field(name=f"Статус события", value=f"{event.state}", inline=True)
#         embed.add_field(name=f"Время события", value=f"{event.created.strftime('%d.%m.%Y %H:%M')}", inline=True)
#         embed.add_field(name=f"", value=f"", inline=False)
#         embed.add_field(name=f"Наличие варов", value=f"{_extra[0]}", inline=True)
#         embed.add_field(name=f"Ночной", value=f"{_extra[0]}", inline=True)
#         embed.set_footer(text="✅\tприсутствовал\n⏲\tопоздал\n⚔\t️вары (только для РЛ)\n🌃\tночь (только для РЛ)")
#         return embed
#
#     def make_embed_stated_event(self, ctx: Context, message: discord.Message):
#         event = self.get_active_event(message=message)
#         embed = self._make_embed(ctx=ctx, message=message)
#         embed.colour = discord.Colour.blue()
#         return embed
#
#     def make_embed_finished_event(self, ctx: Context, message: discord.Message):
#         event = self.get_active_event(message=message)
#         embed = self._make_embed(ctx=ctx, message=message)
#         embed.colour = discord.Colour.green()
#         embed.remove_footer()
#
#         economy = embed.fields[0].value
#         if event.capacity_unit == GameEventCapacityUnit.MINUTE:
#             economy += f"Фактическое время:\t{event.quantity} минут\n"
#         if event.capacity_unit == GameEventCapacityUnit.VISIT:
#             economy += f"Фактическое количество:\t{event.quantity} посещений\n"
#         if event.capacity_unit == GameEventCapacityUnit.THING:
#             economy += f"Фактическое количество:\t{event.quantity} боссов\n"
#
#         reward = self.calculate_reward(event.cost, event.capacity, event.quantity)
#         economy += f"Итог: {reward} дкп"
#
#         embed.set_field_at(index=0, name=f"Бухгалтерия", value=economy, inline=False)
#
#         user_full_list = '\n'.join(list(event.users.filter(
#             state=GameEventUserState.FULL).values_list('user_display_name', flat=True)))
#         user_late_list = '\n'.join(list(event.users.filter(
#             state=GameEventUserState.LATE).values_list('user_display_name', flat=True)))
#
#         embed.add_field(name=f"", value=f"", inline=False)
#         embed.add_field(name=f"Участники", value=f"{user_full_list}", inline=True)
#         embed.add_field(name=f"Опоздали", value=f"{user_late_list}", inline=True)
#
#         return embed
#
#     def make_embed_canceled_event(self, ctx: Context, message: discord.Message):
#         embed = self._make_embed(ctx=ctx, message=message)
#         embed.colour = discord.Colour.red()
#         embed.remove_footer()
#         return embed
#
#     def calculate_reward(self, cost, capacity, quantity, lateness_percent=None, nightly_percent=None) -> int:
#         reward = cost * float(quantity) / float(capacity)
#         if lateness_percent:
#             reward = reward * float(lateness_percent / 100)
#         if nightly_percent:
#             reward = reward + float(nightly_percent * reward) / 100
#         return int(round(reward, 1))
#
#     def add_user_to_event(self, event: GameEvent, user: discord.User, state: GameEventUserState) -> GameEventUser:
#         event_user = GameEventUser(
#             event=event,
#             user_id=user.id,
#             user_name=user.name,
#             user_display_name=user.display_name,
#             state=state,
#         )
#         lateness_percent = event.lateness_percent if state == GameEventUserState.LATE else None
#         event_user.reward = self.calculate_reward(event.cost, event.capacity, event.quantity,
#                                                   lateness_percent=lateness_percent)
#         return event_user
#
#     def add_author_to_event(self, event: GameEvent):
#         event_author, created = GameEventUser.objects.get_or_create(
#             event=event,
#             user_id=event.author_id
#         )
#         event_author.user_name = event.author_name
#         event_author.user_display_name = event.author_display_name
#         event_author.state = GameEventUserState.FULL
#         event_author.reward = self.calculate_reward(event.cost, event.capacity, event.quantity)
#         event_author.save()
#
#     def save_event(self, message: discord.Message) -> GameEvent:
#         event = self.get_active_event(message=message)
#         event_reactions = self.active_event_reactions[message.id]
#
#         event.state = GameEventState.FINISHED
#         event.full_clean()
#         event.save()
#
#         event_users = []
#
#         for user, reaction in event_reactions.items():
#             user_reaction = GameEventUserState.NONE
#             if reaction:
#                 user_reaction = self.USER_REACTIONS.get(reaction.emoji, GameEventUserState.NONE)
#             event_user_state = user_reaction
#             event_user = self.add_user_to_event(event=event, user=user, state=event_user_state)
#             event_users.append(event_user)
#
#         GameEventUser.objects.bulk_create(event_users)
#
#         self.add_author_to_event(event=event)
#         return event
#
#
# class GameEventTemplateSelect(discord.ui.Select):
#     def __init__(self, ctx: Context, bot: EveBot, service: GameEventService):
#         super().__init__(
#             placeholder="Выбрать событие...",
#             min_values=1,
#             max_values=1,
#             row=0,
#         )
#         self.ctx: Context = ctx
#         self.bot = bot
#         self.service: GameEventService = service
#         self.__fill_options()
#
#     def __fill_options(self) -> None:
#         event_templates = self.service.get_templates()
#         for event_template in event_templates:
#             self.add_option(
#                 label=f"{event_template.title}",
#                 value=f"{event_template.id}",
#                 description=f"{event_template.description}",
#             )
#         if not event_templates:
#             self.add_option(
#                 label='Требуется создать шаблоны',
#                 value='__index',
#                 description='',
#             )
#
#     async def callback(self, interaction: discord.Interaction):
#         assert self.view is not None
#         value = self.values[0]
#         if value == '__index':
#             await interaction.message.delete()
#
#         message: discord.Message = interaction.message
#         author: discord.User = self.ctx.message.author
#         template = self.service.get_template(template_id=int(value))
#         event = self.service.add_active_event(message=message, author=author, template=template)
#         embed = self.service.make_embed_stated_event(ctx=self.ctx, message=message)
#         await interaction.response.edit_message(content=None, embed=embed, view=None)
#         self.view.stop()
#
#
# class GameEventTemplateView(discord.ui.View):
#
#     def __init__(self, ctx: Context, service: GameEventService):
#         super().__init__(timeout=None)
#         self.ctx: Context = ctx
#         self.service: GameEventService = service
#         self.add_item(GameEventTemplateSelect(ctx=ctx, bot=ctx.bot, service=service))
#
#
# class GameEventButtonView(discord.ui.View):
#
#     def __init__(self, ctx: Context, service: GameEventService):
#         super().__init__(timeout=None)
#         self.ctx: Context = ctx
#         self.service: GameEventService = service
#
#     @discord.ui.button(label="Завершить", style=discord.ButtonStyle.green)
#     async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
#         message: discord.Message = interaction.message
#
#         event = self.service.get_active_event(message=message)
#         if not event.quantity:
#             modal = GameEventQuantityModal(ctx=self.ctx, service=self.service,
#                                            parent=self, event=event)
#             await interaction.response.send_modal(modal)
#         else:
#             self.service.save_event(message=message)
#             embed = self.service.make_embed_finished_event(ctx=self.ctx, message=message)
#             await interaction.response.edit_message(content=None, embed=embed, view=None)
#             self.stop()
#
#     @discord.ui.button(label="Отменить", style=discord.ButtonStyle.red)
#     async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
#         message: discord.Message = interaction.message
#         event: GameEvent = self.service.active_events[message.id]
#         event.state = GameEventState.CANCELED
#         embed = self.service.make_embed_canceled_event(ctx=self.ctx, message=message)
#         await interaction.response.edit_message(content=None, embed=embed, view=None)
#         self.stop()
#
#
# class GameEventQuantityModal(discord.ui.Modal):
#     quantity = discord.ui.TextInput(label="Количество минут или количество боссов", placeholder="1",
#                                     required=True, style=discord.TextStyle.short)
#
#     def __init__(self, ctx: Context, service: GameEventService, parent, event: GameEvent):
#         super().__init__(title=f"Введите количество", timeout=None)
#
#         self.ctx: Context = ctx
#         self.service: GameEventService = service
#         self.parent: GameEventButtonView = parent
#         self.event: GameEvent = event
#
#     async def on_submit(self, interaction: discord.Interaction) -> None:
#         self.service.set_quantity_event(interaction.message, quantity=int(self.quantity.value))
#         self.service.save_event(interaction.message)
#         embed = self.service.make_embed_finished_event(ctx=self.ctx, message=interaction.message)
#         await interaction.response.edit_message(content=None, embed=embed, view=None)
#         self.parent.stop()
#         self.stop()
#
#
# class GameActivity(commands.Cog):
#     def __init__(self, bot):
#         self.bot = bot
#         self.service: GameEventService = GameEventService()
#
#     @commands.hybrid_command(name="event", aliases=["e", "у", "умуте"])
#     async def event(self, ctx: Context) -> None:
#
#         await ctx.message.delete()
#
#         view = GameEventTemplateView(ctx=ctx, service=self.service)
#         event_message: discord.Message = await ctx.send(None, embed=None, view=view)
#
#         await view.wait()
#
#         view = GameEventButtonView(ctx=ctx, service=self.service)
#
#         await event_message.edit(content=None, view=view)
#
#         for event_reaction in ['✅', '⏲️', '⚔️', '🌃']:
#             await event_message.add_reaction(event_reaction)
#
#         await view.wait()
#         await event_message.clear_reactions()
#
#     @commands.Cog.listener()
#     async def on_reaction_add(self, reaction: discord.Reaction, user: discord.Member):
#
#         message: discord.Message = reaction.message
#         guild: discord.Guild = self.bot.get_guild(message.guild.id)
#
#         if not guild:  # In DM, ignore
#             return
#
#         if user.bot:  # Ignore Bot reaction
#             return
#
#         is_user_reaction = self.service.check_user_reaction(reaction)
#         user_reacted = self.service.check_user_reacted(message, user)
#
#         if is_user_reaction and not user_reacted:
#             self.service.add_reaction(message, user, reaction)
#         elif is_user_reaction and user_reacted:  # Re-reacted
#             self.service.remove_reaction(message, user)
#             await message.remove_reaction(user_reacted.emoji, user)
#             self.service.add_reaction(message, user, reaction)
#         elif not is_user_reaction:
#             await message.remove_reaction(reaction.emoji, user)
#
#     @commands.Cog.listener()
#     async def on_reaction_remove(self, reaction: discord.Reaction, user: discord.Member):
#         emoji = str(reaction.emoji)
#         message: discord.Message = reaction.message
#         guild: discord.Guild = self.bot.get_guild(message.guild.id)
#
#         if not guild:  # In DM, ignore
#             return
#
#         if user.bot:  # Ignore Bot reaction
#             return
#
#         is_user_reaction = self.service.check_user_reaction(reaction)
#
#         if is_user_reaction:
#             self.service.remove_reaction(message, user)
#             await message.remove_reaction(emoji, user)




class ActivityEventCommands(commands.Cog):

    def __init__(self, bot: EveBot):
        self.bot: EveBot = bot
        self._active_event: Optional[ActivityEvent] = None
        self._message_cache: dict[int, discord.Message] = {}

    @cache.cache()
    async def _activity_channels(self, ctx: EveContext) -> List[discord.TextChannel]:
        guild = ctx.guild
        activity_channels = list(ActivityChannel.objects.filter(guild_id=guild.id).values_list('channel_id', flat=True))
        guild_activity_channels = [ch for ch in self.bot.get_all_channels()
                                   if ch.id in activity_channels]
        return guild_activity_channels

    async def _on_command_error(self, ctx: EveContext, error):
        if isinstance(error, NotActivityChannel):
            activity_channels: List[discord.TextChannel] = await self._activity_channels(ctx=ctx)
            await ctx.send(f'Это не мой канал :(...\n'
                           f'Перейди сюда >>> {" ".join([ch.mention for ch in activity_channels])}', ephemeral=True)
        else:
            await ctx.send(str(error), ephemeral=True)

    async def cog_command_error(self, ctx: EveContext, error):
        await self._on_command_error(ctx, error)

    @cache.cache()
    async def get_activity_templates(self) -> List[ActivityTemplate]:
        templates = ActivityTemplate.objects.all()
        return list(templates)

    # async def template_id_autocomplete(self, interaction: discord.Interaction,
    #                                current: str) -> list[app_commands.Choice[int]]:
    #     templates = await self.get_activity_templates()
    #     results = fuzzy.finder(current, templates, key=lambda t: t.title, raw=True)
    #     return [
    #         app_commands.Choice(name=get_shortened_string(length, start, template.title), value=template.id)
    #         for length, start, template in results[:20]
    #     ]
    #
    # async def create_event(self) -> ActivityEvent:
    #     event = ActivityEvent()
    #     return event
    #
    # @commands.hybrid_group(
    #     name='event',
    #     description='event command'
    # )
    # @is_activity_channel()
    # async def event(self, ctx) -> None:
    #     await ctx.send(f'Event creation', mention_author=False, reference=ctx.message)
    #
    # @event.command(
    #     name='create',
    #     description='Создать событие'
    # )
    # @is_activity_channel()
    # @app_commands.autocomplete(template=template_id_autocomplete)
    # async def event_create(self, ctx: EveContext, template: int, comment: Optional[str]):
    #     # emoji = '✅'
    #     # await ctx.message.add_reaction(emoji)
    #     # ctx.message.type = MessageType.
    #     await ctx.defer()
    #     await asyncio.sleep(3)
    #     msg = await ctx.send(f'...')
    #     print(f'CTX:\t{ctx.message.id}\tMSG:\t{msg.id}')
    #
    #
    #
    # async def event_template_autocomplete(
    #         self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    #     # fruits = ['Banana', 'Pineapple', 'Apple', 'Watermelon', 'Melon', 'Cherry']
    #     templates: List[ActivityTemplate] = ActivityTemplate.objects.all()
    #     return [
    #         app_commands.Choice(name=template.title, value=str(template.id))
    #         for template in templates if current in template.title
    #     ]
    # @event.command(name='create', description='Создание события вручную')
    # @is_activity_channel()
    # # @app_commands.autocomplete(template_id=event_template_autocomplete)
    # async def event_create(self, ctx: EveContext, template_id: str):
    #     # channel = self.get_activity_channel(ctx=ctx)
    #
    #     guild = ctx.guild
    #     channel = ctx.channel
    #     message = ctx.message
    #     a = await ctx.defer()
    #     # activity_event = ActivityEvent(
    #     #     guild_id=guild.id,
    #     #     channel_id=channel.id,
    #     #     message_id=message.id,
    #     #     user_id=ctx.author.id,
    #     #     user_name=ctx.author.name,
    #     #     user_display_name=ctx.author.display_name,
    #     #
    #     #     activity_type=template.activity_type,
    #     #     activity_unit=template.activity_unit,
    #     #     capacity=template.capacity,
    #     #     cost=template.cost,
    #     #     penalty=template.penalty,
    #     #     military=template.military,
    #     #     overnight=template.overnight,
    #     #     title=template.title,
    #     #     description=template.description,
    #     #     state=EventState.STARTED
    #     # )
    #     #
    #     # self._active_event = activity_event
    #     msg = await ctx.send(f'Event creation command (to channel)', mention_author=False, reference=ctx.message)
    #     print(f'EVENT: {message.id}\tMSG: {msg.id}\t{template_id}')
    # @event.error
    # async def event_error(self, ctx: Context, error: Exception):
    #     await ctx.send(str(error), ephemeral=True)
    #
    #
    # async def templates_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[int]]:
    #     todos = await self.get_todos(interaction.user.id)
    #     results = fuzzy.finder(current, todos, key=lambda t: t.choice_text, raw=True)
    #     return [
    #         app_commands.Choice(name=get_shortened_string(length, start, todo.choice_text), value=todo.id)
    #         for length, start, todo in results[:20]
    #     ]
    #


async def setup(bot):
    await bot.add_cog(ActivityEventCommands(bot))
