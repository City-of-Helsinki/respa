from django.core.management import BaseCommand

from respa_exchange.downloader import sync_from_exchange
from respa_exchange.management.base import configure_console_log, get_active_download_resources
from respa_exchange.models import ExchangeConfiguration


class Command(BaseCommand):
    def handle(self, verbosity, *args, **options):
        if verbosity >= 2:
            configure_console_log()

        exchanges = ExchangeConfiguration.objects.filter(enabled=True)

        for resource in get_active_download_resources(exchanges):
            sync_from_exchange(resource)
