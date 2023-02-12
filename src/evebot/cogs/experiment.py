from __future__ import annotations

import logging
import re

import discord
import platform
from typing import Optional
from discord import app_commands
from discord.ext import commands

from evebot.bot import EveBot, EveContext
from activity.models import *


log = logging.getLogger(__name__)


RESPAWN_RE = re.compile('\D+\s\d{2}:\d{2}\*?\s+\d{2,3}%')


class ExpFlags(commands.FlagConverter):
    title: str = commands.flag(name='title', aliases=['name', 'название'], description='Название шаблона', default='TEMPLATE')
    description: str = commands.flag(name='description', aliases=['comment', 'описание'], description='Описание', default='')


class ExperimentCog(commands.Cog):
    def __init__(self, bot: EveBot):
        self.bot: EveBot = bot

    async def cog_app_command_error(self, interaction: discord.Interaction,
                                    error: app_commands.AppCommandError) -> None:
        log.error(f'Error handled by "cog_app_command_error": {str(error)}')
        await interaction.response.send_message(f'Что-то пошло не так \N{SKULL AND CROSSBONES}', ephemeral=True)

    async def cog_command_error(self, ctx: EveContext, error: Exception) -> None:
        log.error(f'Error handled by "cog_command_error": {str(error)}')
        await ctx.send(f'Что-то пошло не так \N{SKULL AND CROSSBONES}', ephemeral=True)

    @commands.hybrid_command(
        name='exp',
        with_app_command=False
    )
    async def exp(self, ctx: EveContext, description: Optional[str]) -> None:
        await ctx.send(ctx.tick(False, '...'), reference=ctx.message)

    @commands.hybrid_command(
        name='exphyb'
    )
    async def exphyb(self, ctx: EveContext, args: ExpFlags) -> None:
        description = args.description or '...'
        if RESPAWN_RE.match(description):
            description = '\n'.join([rs.lstrip().rstrip() for rs in RESPAWN_RE.findall(description)])
            description = f'```fix\n' \
                          f'{description}```'

        embed = discord.Embed(colour=discord.Colour.dark_teal())
        embed.description = description
        await ctx.send(embed=embed, reference=ctx.message)

    @app_commands.command(
        name='expapp'
    )
    async def expapp(self, interaction: discord.Interaction, description: Optional[str]):
        raise Exception("ERROR!")


async def setup(bot):
    await bot.add_cog(ExperimentCog(bot))
