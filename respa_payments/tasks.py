
# -*- coding: utf-8 -*-

import datetime
from celery import task
from celery.utils.log import get_task_logger
from resources.models.reservation import Reservation

LOG = get_task_logger(__name__)


@task(ignore_results=True)
def clear_unpaid_reservations():
    time_ago = datetime.datetime.now() - datetime.timedelta(minutes=15)
    reservations = Reservation.objects.filter(state=Reservation.REQUESTED, begin__lt=time_ago)
    reservations.update(state=Reservation.DENIED)
