from django.core.management.base import BaseCommand
from django.utils import timezone

from ...bots import EveBot
from django.conf import settings


class Command(BaseCommand):
    help = ''

    def add_arguments(self, parser):
        parser.add_argument('port', nargs='+', type=int)

    def handle(self, *args, **kwargs):
        bot = EveBot()
        bot.run(settings.EVE_TOKEN)
