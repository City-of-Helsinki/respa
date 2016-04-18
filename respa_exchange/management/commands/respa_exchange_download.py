import logging

import sys
from django.core.management.base import BaseCommand

from respa_exchange.downloader import sync_from_exchange
from respa_exchange.models import ExchangeResource, ExchangeConfiguration

rx_logger = logging.getLogger("respa_exchange")


class Command(BaseCommand):
    def handle(self, verbosity, *args, **options):
        if verbosity >= 2:
            self.configure_console_log()

        for exchange in ExchangeConfiguration.objects.filter(
            enabled=True
        ):
            for ex_resource in ExchangeResource.objects.filter(
                sync_to_respa=True,
                exchange=exchange,
            ):
                ex_resource.exchange = exchange  # Allow sharing the EWS session
                sync_from_exchange(ex_resource)

    def configure_console_log(self):
        rx_logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(stream=sys.stdout)
        handler.setFormatter(logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s: %(message)s",
            datefmt=logging.Formatter.default_time_format
        ))
        rx_logger.addHandler(handler)
