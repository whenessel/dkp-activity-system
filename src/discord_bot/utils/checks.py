from typing import Callable, TypeVar

from discord.ext import commands

T = TypeVar("T")


def is_owner() -> Callable[[T], T]:
    """
    This is a custom check to see if the user executing the command is an owner of the bot.
    """
    async def predicate(context: commands.Context) -> bool:
        if context.author.id not in context.bot.owner_ids:
            raise UserNotOwner
        return True

    return commands.check(predicate)
