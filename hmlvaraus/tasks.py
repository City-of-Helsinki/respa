
# -*- coding: utf-8 -*-

from datetime import timedelta
from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist


@shared_task
def set_reservation_renewal(reservation_id):
    from hmlvaraus.models.hml_reservation import HMLReservation
    try:
        instance = HMLReservation.objects.get(pk=reservation_id)
    except ObjectDoesNotExist:
        return False
    reservation = instance.reservation
    if reservation.state == reservation.CONFIRMED:
        instance.is_paid = False
        instance.save()
        reservation.end = reservation.end + timedelta(days=365)
        reservation.save()


@shared_task
def set_reservation_cancel(reservation_id):
    from hmlvaraus.models.hml_reservation import HMLReservation
    try:
        instance = HMLReservation.objects.get(pk=reservation_id)
    except ObjectDoesNotExist:
        return False
    if not instance.is_paid:
        reservation.state = reservation.CANCELLED
        reservation.save()

