from typing import Union

import discord
from discord import app_commands
from discord.ext import commands
from activity.models import EventTemplate


class EventTemplateTransformer(app_commands.Transformer):
    async def transform(self, interaction: discord.Interaction, value: Union[str, int]) -> EventTemplate:
        event_template = EventTemplate.objects.get(id=int(value))
        return event_template
