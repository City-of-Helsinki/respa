
# -*- coding: utf-8 -*-

import datetime
from celery import task
from celery.utils.log import get_task_logger
from resources.models.reservation import Reservation
from respa_payments.models import Order

LOG = get_task_logger(__name__)


@task(ignore_results=True)
def clear_unpaid_reservations():
    time_ago = datetime.datetime.now() - datetime.timedelta(minutes=15)
    requested_payments = Order.objects.filter(payment_service_success=False,
                                              reservation__state=Reservation.REQUESTED,
                                              created_at__lt=time_ago)
    for payment in requested_payments:
        reservation = payment.reservation
        reservation.state = Reservation.DENIED
        reservation.save()
