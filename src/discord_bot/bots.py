import os
import platform
import importlib
import pkgutil
import discord
from discord.ext import commands
from django.conf import settings
from .exceptions import UserNotOwner


def search_from_django() -> list:
    cogs_list = []
    if settings.configured:
        for app in settings.EVE_INSTALLED_COGS:
            cogs_module_name = app + ".cogs"
            try:
                cogs_module = importlib.import_module(cogs_module_name)
                for importer, modname, ispkg in pkgutil.iter_modules(cogs_module.__path__):
                    cogs_list.append(f"{cogs_module_name}.{modname}")
            except ImportError:
                pass
    return cogs_list


class EveBot(commands.Bot):
    extensions = []

    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(
            command_prefix=commands.when_mentioned_or(settings.EVE_PREFIX),
            intents=intents,
            help_command=None,
            enable_debug_events=True,
        )

    async def autodiscover_cogs(self):
        for cog in self.extensions + search_from_django():
            try:
                await self.load_extension(cog)
                # print(f'Loaded extension {cog}')
            except Exception as exc:
                print(f'Could not load extension \'{cog}\' due to {exc.__class__.__name__}: {exc}')

    async def setup_hook(self):
        await self.autodiscover_cogs()
        self.owner_ids = settings.EVE_OWNERS

    async def on_ready(self):
        # print(f"Logged in as {self.user} (ID: {self.user.id})")
        # print(f"discord_evebot.py API version: {discord.__version__}")
        # print(f"Python version: {platform.python_version()}")
        # print(f"Running on: {platform.system()} {platform.release()} ({os.name})")
        ...

    async def on_message(self, message: discord.Message) -> None:
        if message.author == self.user or message.author.bot:
            return
        await self.process_commands(message)

    async def on_command_error(self, context: commands.Context, error) -> None:
        if isinstance(error, commands.CommandOnCooldown):
            minutes, seconds = divmod(error.retry_after, 60)
            hours, minutes = divmod(minutes, 60)
            hours = hours % 24
            embed = discord.Embed(
                description=f"**Please slow down** - You can use this command again "
                            f"in {f'{round(hours)} hours' if round(hours) > 0 else ''} "
                            f"{f'{round(minutes)} minutes' if round(minutes) > 0 else ''} "
                            f"{f'{round(seconds)} seconds' if round(seconds) > 0 else ''}.",
                color=0xE02B2B
            )
            await context.send(embed=embed)
        elif isinstance(error, UserNotOwner):
            embed = discord.Embed(
                description="You are not the owner of the bot!",
                color=0xE02B2B
            )
            await context.send(embed=embed)
            print(f"{context.author} (ID: {context.author.id}) tried to execute an owner only command "
                  f"in the guild {context.guild.name} (ID: {context.guild.id}), "
                  f"but the user is not an owner of the bot.")
        elif isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                description=f"You are missing the permission(s) "
                            f"'{', '.join(error.missing_permissions)}' to execute this command!",
                color=0xE02B2B
            )
            await context.send(embed=embed)
        elif isinstance(error, commands.BotMissingPermissions):
            embed = discord.Embed(
                description="I am missing the permission(s) `" + ", ".join(
                    error.missing_permissions) + "` to fully perform this command!",
                color=0xE02B2B
            )
            await context.send(embed=embed)
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                title="Error!",
                # We need to capitalize because the command arguments have no capital letter in the code.
                description=str(error).capitalize(),
                color=0xE02B2B
            )
            await context.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Error!",
                # We need to capitalize because the command arguments have no capital letter in the code.
                description=str(f"CHECK SERVER LOGS!").capitalize(),
                color=0xE02B2B
            )
            await context.send(embed=embed)
            raise error
