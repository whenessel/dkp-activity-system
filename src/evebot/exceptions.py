import typing as t
from discord.ext import commands


class NotEventChannel(commands.CheckFailure):
    """
    Thrown when a user is attempting something into not configured EventChannel.
    """

    def __init__(self, message: t.Optional[str] = None):
        super().__init__(message or "This command cannot be used in this TextChannel")


class NotEventModerator(commands.CheckFailure):
    """
    Thrown when a user is attempting something into channel...
    """

    def __init__(self, message: t.Optional[str] = None):
        super().__init__(message or "This command cannot be used not event moderator")
