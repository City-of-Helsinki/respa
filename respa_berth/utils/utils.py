
# -*- coding: utf-8 -*-

from datetime import timedelta

from rest_framework.filters import OrderingFilter

from django.core.exceptions import FieldDoesNotExist
from django.db.models.fields.reverse_related import ForeignObjectRel, OneToOneRel
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from respa_berth import tasks
from respa_berth.models.berth_reservation import BerthReservation
from respa_berth.models.berth import Berth
from resources.models.reservation import Reservation
from respa_berth.models.purchase import Purchase
import time

@receiver(post_save, sender=Purchase)
def set_reservation_renew(sender, instance, **kwargs):
    if kwargs.get('created'):
        cancel_eta = timezone.now() + timedelta(minutes=20)
        tasks.cancel_failed_reservation.apply_async((instance.id,), eta=cancel_eta)

def test_group_send_initial_renewal_notifications():
    test_group_list = [
        'Rökman Rauno',
        'Varjonen Jyrki',
        'Nieminen Juha',
        'Kokkonen Jukka',
        'Sajantola Sonja'
    ]
    reservations = BerthReservation.objects.filter(reservation__reserver_name__in=test_group_list, reservation__begin='2017-11-30 22:00:00+00:00', reservation__end='2018-05-31 21:00:00+00:00', reservation__state=Reservation.CONFIRMED, child=None)
    if len(reservations) != 5:
        print('Reservation count doesnt match with test group user count. Exiting...')
        return
    for reservation in reservations:
        tasks.send_initial_renewal_notification.delay(reservation.id)

def send_initial_renewal_notifications():
    test_group_list = [
        'Rökman Rauno',
        'Varjonen Jyrki',
        'Nieminen Juha',
        'Kokkonen Jukka',
        'Sonja Sajantola'
    ]
    reservations = BerthReservation.objects.filter(reservation__end='2018-05-31 21:00:00+00:00', reservation__state=Reservation.CONFIRMED, child=None).exclude(reservation__reserver_name__in=test_group_list)
    for reservation in reservations:
        tasks.send_initial_renewal_notification.delay(reservation.id)

def set_reserved_berths_unreservable():
    reservations = BerthReservation.objects.filter(reservation__end__gte=timezone.now(), reservation__state=Reservation.CONFIRMED)
    berths = Berth.objects.filter(berth_reservations__in=reservations, resource__reservable=True)
    for berth in berths:
        resource = berth.resource
        resource.reservable = False
        resource.save()

class RelatedOrderingFilter(OrderingFilter):
    """
    Extends OrderingFilter to support ordering by fields in related models.
    """

    def is_valid_field(self, model, field):
        """
        Return true if the field exists within the model (or in the related
        model specified using the Django ORM __ notation)
        """
        components = field.split('__', 1)
        try:

            field = model._meta.get_field(components[0])

            if isinstance(field, OneToOneRel):
                return self.is_valid_field(field.related_model, components[1])

            # reverse relation
            if isinstance(field, ForeignObjectRel):
                return self.is_valid_field(field.model, components[1])

            # foreign key
            if field.rel and len(components) == 2:
                return self.is_valid_field(field.rel.to, components[1])
            return True
        except FieldDoesNotExist:
            return False

    def remove_invalid_fields(self, queryset, fields, view, foo):
        return [term for term in fields
                if self.is_valid_field(queryset.model, term.lstrip('-'))]
