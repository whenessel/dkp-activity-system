
import discord
from discord import app_commands
from discord.ext import commands
from evebot.bot import EveBot, EveContext
from activity.models import *
from evebot.exceptions import NotEventChannel, NotEventModerator


def event_channel_only():
    async def predicate(interaction: discord.Interaction) -> bool:
        event_channels = EventChannel.objects.filter(guild_id=interaction.guild.id, channel_id=interaction.channel.id)

        if not event_channels.exists():
            raise NotEventChannel

        return True

    return app_commands.check(predicate)


def event_moderator_only():
    async def predicate(interaction: discord.Interaction) -> bool:
        event_moderator = EventModerator.objects.filter(guild_id=interaction.guild.id, member_id=interaction.user.id)

        if not event_moderator.exists():
            raise NotEventModerator

        return True

    return app_commands.check(predicate)
