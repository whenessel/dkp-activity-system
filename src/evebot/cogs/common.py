from __future__ import annotations

import logging
import discord
import platform
from typing import Optional
from discord import app_commands
from discord.ext import commands
from evebot.bot import EveBot, EveContext


log = logging.getLogger(__name__)


class CommonCog(commands.Cog):
    def __init__(self, bot: EveBot):
        self.bot: EveBot = bot

    @commands.hybrid_command(
        name='botinfo',
        description='Краткая информация о боте',
        with_app_command=False
    )
    async def botinfo(self, ctx: EveContext) -> None:
        embed = discord.Embed(color=discord.Colour.gold(),
                              description='Используется для работы ДКП системы')
        embed.set_author(name='Информация')
        embed.add_field(name='Владелец:', value='Aliace#2031', inline=True)
        embed.add_field(name='Python Version:', value=f'{platform.python_version()}', inline=True)
        prefixes = '\n'.join([f'\t{prefix if not "@" in prefix else prefix+" "}botinfo'
                              for prefix in self.bot.get_guild_prefixes(ctx.guild)])
        embed.add_field(
            name='Префикс:',
            value=f'/ для команд приложения или {self.bot.prefix} для текстовых команд.\n'
                  f'Варианты использования для текущего сервера:\n'
                  f'{prefixes}\n',
            inline=False
        )
        embed.set_footer(text=f'Запросил {ctx.author}')
        await ctx.send(embed=embed, mention_author=False, reference=ctx.message)

    @commands.hybrid_command(
        name='ping',
        description='Проверка доступности бота',
        with_app_command=False
    )
    async def ping(self, ctx: EveContext) -> None:
        embed = discord.Embed(
            color=discord.Colour.gold(),
            title='🏓 Pong!',
            description=f'Время ответа {round(self.bot.latency * 1000)}ms.'
        )
        await ctx.send(embed=embed, mention_author=False, reference=ctx.message)


async def setup(bot):
    await bot.add_cog(CommonCog(bot))
