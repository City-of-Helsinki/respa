from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from resources.models.base import ModifiableModel
from resources.models.reservation import Reservation
from resources.models.resource import DurationSlot


class Sku(ModifiableModel):
    duration_slot = models.ForeignKey(DurationSlot, related_name='skus', db_index=True, null=True, on_delete=models.SET_NULL)
    price = models.DecimalField(verbose_name=_('Price'), max_digits=6, decimal_places=2, default=0.00)
    vat = models.DecimalField(verbose_name=_('VAT'), max_digits=6, decimal_places=2, default=24.00)
    name = models.CharField(verbose_name=_('Name'), max_length=200)

    class Meta:
        verbose_name = _('Stock keeping unit')
        verbose_name_plural = _('Stock keeping units')

    def __str__(self):
        return self.name


class Order(ModifiableModel):
    sku = models.ForeignKey(Sku, db_index=True, null=True, on_delete=models.SET_NULL)
    reservation = models.OneToOneField(Reservation, db_index=True, null=True, on_delete=models.SET_NULL,)
    verification_code = models.CharField(verbose_name=_('Verification code'), max_length=40, null=False,
                                         blank=True, default='')
    order_process_started = models.DateTimeField(verbose_name=_('Order process started'), blank=True, null=True)
    order_process_success = models.DateTimeField(verbose_name=_('Order process success'), blank=True, null=True)
    order_process_failure = models.DateTimeField(verbose_name=_('Order process failure'), blank=True, null=True)
    order_process_notified = models.DateTimeField(verbose_name=_('Order process notified'), blank=True, null=True)
    order_process_log = models.TextField(
        verbose_name=_('Order process log'), blank=True, null=True
    )
    payment_service_timestamp = models.DateTimeField(verbose_name=_('Payment service timestamp'), blank=True, null=True)
    payment_service_amount = models.DecimalField(max_digits=10, decimal_places=2,
                                                 verbose_name=_('Payment service amount'), default=0)
    payment_service_currency = models.CharField(
        verbose_name=_('Payment service currency'), max_length=100, blank=True, null=True
    )
    payment_service_status = models.CharField(
        verbose_name=_('Payment service status'), max_length=100, blank=True, null=True
    )
    payment_service_success = models.BooleanField(default=False)
    payment_service_method = models.IntegerField(blank=True, null=True)
    payment_service_return_authcode = models.CharField(
        verbose_name=_('Payment service return authcode'),
        max_length=100, blank=True,
        null=True
    )
