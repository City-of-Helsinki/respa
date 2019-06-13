import logging

from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from payments.models import Order

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sets "waiting" orders that are too old as "expired".'

    @atomic
    def handle(self, *args, **options):
        logger.info('Updating expired orders...')
        num_of_updated = Order.update_expired()
        logger.info('Done, {} order(s) got expired.'.format(num_of_updated))
