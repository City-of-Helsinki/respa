import logging

from django.core.management import BaseCommand

from respa_exchange.downloader import sync_from_exchange
from respa_exchange.management.base import configure_logging, get_active_download_resources, select_resources
from respa_exchange.models import ExchangeConfiguration


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('-l', action='store_true', dest='list', default=False,
                            help='List supported exchange resources')
        parser.add_argument('--resource', action='append', dest='resources',
                            help='Sync only specified resource(s)')

    def handle(self, verbosity, *args, **options):
        if verbosity >= 2:
            configure_logging(level=logging.DEBUG)

        exchanges = ExchangeConfiguration.objects.filter(enabled=True)

        if options['list']:
            for ex in exchanges:
                print(ex)
                for res in get_active_download_resources([ex]):
                    print('%5s: %s' % (res.id, res))
            return

        resources = get_active_download_resources(exchanges)
        if options['resources']:
            resources = select_resources(resources, options['resources'])

        for resource in resources:
            sync_from_exchange(resource)
