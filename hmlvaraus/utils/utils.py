
# -*- coding: utf-8 -*-

from datetime import timedelta

from rest_framework.filters import OrderingFilter

from django.core.exceptions import FieldDoesNotExist
from django.db.models.fields.reverse_related import ForeignObjectRel, OneToOneRel
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from hmlvaraus import tasks
from hmlvaraus.models.hml_reservation import HMLReservation


@receiver(post_save, sender=HMLReservation)
def set_reservation_renew(sender, instance, **kwargs):
    if kwargs.get('created'):
        cancel_eta = instance.reservation.begin + timedelta(days=30)
        if cancel_eta > timezone.now():
            tasks.set_reservation_cancel.apply_async((instance.id,), eta=cancel_eta)
        tasks.set_reservation_renewal.apply_async((instance.id,), eta=instance.reservation.end)


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
