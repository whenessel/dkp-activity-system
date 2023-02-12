import errno
import os
import re
import socket
import sys
from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


from django.utils import autoreload
from django.utils.regex_helper import _lazy_re_compile

from evebot.bot import EveBot


class Command(BaseCommand):
    help = "Starts a lightweight EVE discord bot."

    bot_klass: EveBot = EveBot

    requires_system_checks = []
    stealth_options = ("shutdown_message",)
    suppressed_base_arguments = {"port", "--verbosity", "--traceback"}

    def add_arguments(self, parser):
        parser.add_argument("port", nargs="?", type=int)
        parser.add_argument(
            "--nothreading",
            action="store_false",
            dest="use_threading",
            help="Tells Django to NOT use threading.",
        )
        parser.add_argument(
            "--noreload",
            action="store_false",
            dest="use_reloader",
            help="Tells Django to NOT use the auto-reloader.",
        )
        parser.add_argument(
            "--skip-checks",
            action="store_true",
            help="Skip system checks.",
        )

    def execute(self, *args, **options):
        if options["no_color"]:
            # We rely on the environment because it's currently the only
            # way to reach WSGIRequestHandler. This seems an acceptable
            # compromise considering `runserver` runs indefinitely.
            os.environ["DJANGO_COLORS"] = "nocolor"
        super().execute(*args, **options)

    def get_handler(self, *args, **options):
        return self.bot_klass()

    def handle(self, *args, **options):
        self.run(**options)

    def run(self, **options):
        """Run the server, using the autoreloader if needed."""
        use_reloader = options["use_reloader"]

        if use_reloader:
            autoreload.run_with_reloader(self.inner_run, **options)
        else:
            self.inner_run(None, **options)

    def inner_run(self, *args, **options):
        autoreload.raise_last_exception()

        threading = options["use_threading"]
        shutdown_message = options.get("shutdown_message", "")
        quit_command = "CTRL-BREAK" if sys.platform == "win32" else "CONTROL-C"

        if not options["skip_checks"]:
            self.stdout.write("Performing system checks...\n\n")
            self.check(display_num_errors=True)

        # self.check_migrations()

        now = datetime.now().strftime("%B %d, %Y - %X")
        self.stdout.write(now)
        self.stdout.write(
            (
                "Django version %(version)s, using settings %(settings)r\n"
                "Starting EveBot...\n"
                "Quit the server with %(quit_command)s."
            )
            % {
                "version": self.get_version(),
                "settings": settings.SETTINGS_MODULE,
                "quit_command": quit_command,
            }
        )

        try:
            handler = self.get_handler(*args, **options)
            handler.run(settings.EVE_TOKEN, log_handler=None)
        except OSError as e:
            # Use helpful error messages instead of ugly tracebacks.
            ERRORS = {
                errno.EACCES: "You don't have permission to access that port.",
                errno.EADDRINUSE: "That port is already in use.",
                errno.EADDRNOTAVAIL: "That IP address can't be assigned to.",
            }
            try:
                error_text = ERRORS[e.errno]
            except KeyError:
                error_text = e
            self.stderr.write("Error: %s" % error_text)
            # Need to use an OS exit because sys.exit doesn't work in a thread
            os._exit(1)
        except KeyboardInterrupt:
            if shutdown_message:
                self.stdout.write(shutdown_message)
            sys.exit(0)

