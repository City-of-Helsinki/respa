import logging
from contextlib import closing

from django.core.management import BaseCommand

from respa_exchange.listener import NotificationListener
from respa_exchange.management.base import configure_console_log


class Command(BaseCommand):
    def handle(self, verbosity, *args, **options):
        if verbosity >= 3:
            configure_console_log(level=logging.DEBUG)
            configure_console_log(level=logging.DEBUG, logger='ExchangeSession')
        elif verbosity >= 2:
            configure_console_log()

        with closing(NotificationListener()) as listener:
            listener.start()
