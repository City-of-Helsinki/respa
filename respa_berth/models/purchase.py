from django.contrib.gis.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from respa_berth.models.berth_reservation import BerthReservation
from resources.models.base import ModifiableModel
from django.core.exceptions import SuspiciousOperation
from django.contrib.auth.models import AnonymousUser
from respa_berth import tasks

class Purchase(ModifiableModel):
    berth_reservation = models.OneToOneField(BerthReservation, verbose_name=_('BerthReservation'), db_index=True, null=True, on_delete=models.SET_NULL)
    purchase_code = models.CharField(verbose_name=_('Purchase code'), max_length=40)
    reserver_name = models.CharField(verbose_name=_('Reserver name'), max_length=100, blank=True)
    reserver_email_address = models.EmailField(verbose_name=_('Reserver email address'), blank=True)
    reserver_phone_number = models.CharField(verbose_name=_('Reserver phone number'), max_length=30, blank=True)
    reserver_address_street = models.CharField(verbose_name=_('Reserver address street'), max_length=100, blank=True)
    reserver_address_zip = models.CharField(verbose_name=_('Reserver address zip'), max_length=30, blank=True)
    reserver_address_city = models.CharField(verbose_name=_('Reserver address city'), max_length=100, blank=True)
    vat_percent = models.IntegerField(choices=[(0, '0'), (10, '10'), (14, '24'), (24, '24')], default=24)
    price_vat = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    product_name = models.CharField(verbose_name=_('Product name'), max_length=100, blank=True)
    purchase_process_started = models.DateTimeField(verbose_name=_('Purchase process started'), default=timezone.now)
    purchase_process_success = models.DateTimeField(verbose_name=_('Purchase process success'), blank=True, null=True)
    purchase_process_failure = models.DateTimeField(verbose_name=_('Purchase process failure'), blank=True, null=True)
    purchase_process_notified = models.DateTimeField(verbose_name=_('Purchase process notified'), blank=True, null=True)
    purchase_process_report_seen = models.DateTimeField(verbose_name=_('Purchase process notified'), blank=True, null=True)
    payment_service_order_number = models.IntegerField(blank=True, null=True)
    payment_service_timestamp = models.CharField(verbose_name=_('Payment service timestamp'), max_length=100, blank=True, null=True)
    payment_service_paid = models.CharField(verbose_name=_('Payment service paid'), max_length=100, blank=True, null=True)
    payment_service_method = models.IntegerField(blank=True, null=True)
    payment_service_return_authcode = models.CharField(verbose_name=_('Reserver address street'), max_length=100, blank=True, null=True)
    finished = models.DateTimeField(verbose_name=_('Purchase finished'), blank=True, null=True)

    def set_success(self):
        if self.purchase_process_failure or self.purchase_process_success or self.purchase_process_notified:
            raise SuspiciousOperation(_('Purchase callback has already returned'))

        self.purchase_process_success = timezone.now()
        self.save()
        tasks.send_confirmation.delay(self.berth_reservation.pk)

    def set_failure(self, user=AnonymousUser()):
        if self.purchase_process_failure or self.purchase_process_success or self.purchase_process_notified:
            raise SuspiciousOperation(_('Purchase callback has already returned'))

        self.purchase_process_failure = timezone.now()
        self.berth_reservation.cancel_reservation(user)
        self.finished = timezone.now()
        self.save()

    def set_notification(self):
        if not self.purchase_process_success:
            raise SuspiciousOperation(_('Purchase success callback has not returned'))

        self.purchase_process_notified = timezone.now()
        self.finished = timezone.now()
        self.save()

    def set_report_seen(self):
        if not self.purchase_process_failure and not self.purchase_process_success:
            raise SuspiciousOperation(_('Invalid purchase state'))
        self.purchase_process_report_seen = timezone.now()
        self.save()

    def set_finished(self):
        if self.finished:
            raise SuspiciousOperation(_('Purchase is already finished'))
        self.finished = timezone.now()
        self.save()

    def report_is_seen(self):
        return bool(self.purchase_process_report_seen)

    def is_success(self):
        return bool(self.purchase_process_success)

    def is_finished(self):
        return bool(self.finished)

    def __str__(self):
        return "%s" % (self.berth_reservation)
