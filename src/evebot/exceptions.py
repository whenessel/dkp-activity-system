from __future__ import annotations
from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands


class NotEventChannel(commands.CheckFailure):
    """
    Thrown when a user is attempting something into not configured EventChannel.
    """

    def __init__(self, message: Optional[str] = None):
        super().__init__(message or "This command cannot be used in this TextChannel")


class NotEventModerator(commands.CheckFailure):
    """
    Thrown when a user is attempting something into channel...
    """

    def __init__(self, message: Optional[str] = None):
        super().__init__(message or "This command cannot be used not event moderator")
