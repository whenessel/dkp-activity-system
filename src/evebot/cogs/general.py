from __future__ import annotations
import discord
import platform
from typing import Optional
from discord import app_commands
from discord.ext import commands
from evebot.bot import EveBot, EveContext


class General(commands.Cog, name="general"):
    def __init__(self, bot):
        self.bot: EveBot = bot

    @commands.hybrid_command(name="botinfo", description="Краткая информация о боте.")
    async def botinfo(self, ctx: EveContext) -> None:
        embed = discord.Embed(color=discord.Colour.gold(), description="Используется")
        embed.set_author(name="Информация")
        embed.add_field(name="Владелец:", value="Aliace#2031", inline=True)
        embed.add_field(name="Python Version:", value=f"{platform.python_version()}", inline=True)
        embed.add_field(
            name="Префикс:",
            value=f"/ для команд приложения или '{self.bot.settings.EVE_PREFIX}' для текстовых команд",
            inline=False
        )
        embed.set_footer(text=f"Запросил {ctx.author}")
        await ctx.send(embed=embed, mention_author=False, reference=ctx.message)

    @commands.hybrid_command(name="ping", description="Проверка доступности бота.")
    async def ping(self, ctx: EveContext) -> None:
        embed = discord.Embed(
            color=discord.Colour.gold(),
            title="🏓 Pong!",
            description=f"Время ответа {round(self.bot.latency * 1000)}ms."
        )
        await ctx.send(embed=embed, mention_author=False, reference=ctx.message)

    @commands.group(
        name="sync",
        description="Синхронизация команд приложения для сервера.",
        invoke_without_command=True
    )
    @commands.is_owner()
    @commands.guild_only()
    async def sync(self, ctx: EveContext, guild_id: Optional[int], copy: bool = False) -> None:
        if guild_id:
            guild = discord.Object(id=guild_id)
        else:
            guild = ctx.guild

        if copy:
            self.bot.tree.copy_global_to(guild=guild)

        commands = await self.bot.tree.sync(guild=guild)
        await ctx.send(
            f"Синхронизировано {len(commands)} команд.",
            mention_author=False, reference=ctx.message
        )

    @sync.command(name="global", description="Синхронизация команд приложения - глобально.")
    @commands.is_owner()
    async def sync_global(self, ctx: EveContext):
        commands = await self.bot.tree.sync(guild=None)
        await ctx.send(
            f"Синхронизировано {len(commands)} команд.",
            mention_author=False, reference=ctx.message
        )


async def setup(bot):
    await bot.add_cog(General(bot))
