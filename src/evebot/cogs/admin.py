from __future__ import annotations

from discord.ext import commands
import asyncio
import logging
import traceback
import discord
import inspect
import platform
from discord import app_commands
from discord.ext import commands
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Union, Optional


if TYPE_CHECKING:
    from typing_extensions import Self
    from evebot.context import EveContext, GuildEveContext
    from evebot.bot import EveBot


log = logging.getLogger(__name__)


class AdminCog(commands.Cog):

    def __init__(self, bot: EveBot):
        self.bot: EveBot = bot
        self._last_result: Optional[Any] = None
        self.sessions: set[int] = set()

    @commands.group(
        name='sync',
        description='Синхронизация команд приложения для сервера',
        invoke_without_command=True)
    @commands.is_owner()
    @commands.guild_only()
    async def sync(self, ctx: GuildEveContext, guild_id: Optional[int], copy: bool = False) -> None:

        if guild_id:
            guild = discord.Object(id=guild_id)
        else:
            guild = ctx.guild

        if copy:
            self.bot.tree.copy_global_to(guild=guild)

        commands = await self.bot.tree.sync(guild=guild)

        content = f'Successfully synced {len(commands)} commands\n'

        for command in commands:
            content += f'**{command.name}**\t{command.description}\n'

        # await ctx.send(content)
        await ctx.send(content, reference=ctx.message)

    @sync.command(
        name='global',
        description='Синхронизация команд приложения - глобально'
    )
    @commands.is_owner()
    async def sync_global(self, ctx: EveContext):

        commands = await self.bot.tree.sync(guild=None)
        content = f'Successfully synced {len(commands)} commands\n'

        for command in commands:
            content += f'**{command.name}**\t{command.description}\n'

        await ctx.send(content, reference=ctx.message)


async def setup(bot):
    await bot.add_cog(AdminCog(bot))
