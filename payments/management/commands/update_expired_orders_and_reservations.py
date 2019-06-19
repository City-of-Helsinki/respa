import logging

from django.core.management.base import BaseCommand
from django.db.transaction import atomic

from payments.models import Order
from resources.models import Reservation

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sets "waiting" orders that are too old as "expired" ' \
           'and cancels reservations that have waited for an order too long.'

    @atomic
    def handle(self, *args, **options):
        logger.info('Updating expired orders and cancelling too old reservations without an order...')
        num_of_updated_orders = Order.update_expired_orders()
        num_of_updated_reservations = Reservation.cancel_too_old_reservations_without_orders()
        logger.info('Done, {} order(s) got expired and {} reservation(s) without an order cancelled.'.format(
            num_of_updated_orders, num_of_updated_reservations)
        )
