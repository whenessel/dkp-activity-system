import operator
from discord.ext import commands


class ImproperlyConfigured(Exception):
    """DisBOT is somehow improperly configured"""
    pass


class UserNotOwner(commands.CheckFailure):
    """
    Thrown when a user is attempting something, but is not an owner of the bot.
    """

    def __init__(self, message="User is not an owner of the bot!"):
        self.message = message
        super().__init__(self.message)
