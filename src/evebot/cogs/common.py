import logging
import platform
import typing as t

import discord
from discord.ext import commands
from discord.mentions import AllowedMentions

if t.TYPE_CHECKING:
    from evebot.bot import EveBot, EveContext


logger = logging.getLogger(__name__)


class CommonCog(commands.Cog):
    def __init__(self, bot: "EveBot"):
        self.bot: "EveBot" = bot

    @commands.hybrid_command(
        name="botinfo", description="Краткая информация о боте", with_app_command=False
    )
    async def botinfo(self, ctx: "EveContext") -> None:
        embed = discord.Embed(
            color=discord.Colour.gold(),
            description="Используется для работы ДКП системы",
        )
        embed.set_author(name="Информация")
        embed.add_field(name="Владелец:", value="Aliace#2031", inline=True)
        embed.add_field(
            name="Python Version:", value=f"{platform.python_version()}", inline=True
        )

        embed.add_field(
            name="Префикс:",
            value=f"/ для команд приложения или "
            f"{self.bot.prefix} для текстовых команд.",
            inline=False,
        )

        admins = []
        for owner_id in ctx.bot.owner_ids:
            member = ctx.guild.get_member(owner_id)
            if member:
                admins.append(member)
        embed.add_field(
            name="Админы:",
            value=f"{' '.join([admin.mention for admin in admins])}",
            inline=False,
        )
        embed.set_footer(text=f"Запросил {ctx.author}")
        await ctx.send(embed=embed, mention_author=False, reference=ctx.message)

    @commands.hybrid_command(
        name="ping", description="Проверка доступности бота", with_app_command=False
    )
    async def ping(self, ctx: "EveContext") -> None:
        embed = discord.Embed(
            color=discord.Colour.gold(),
            title="🏓 Pong!",
            description=f"Время ответа {round(self.bot.latency * 1000)}ms.",
        )
        await ctx.send(embed=embed, mention_author=False, reference=ctx.message)


async def setup(bot):
    await bot.add_cog(CommonCog(bot))
