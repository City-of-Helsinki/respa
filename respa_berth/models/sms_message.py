from django.contrib.gis.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from respa_berth.models.berth_reservation import BerthReservation
from resources.models.base import ModifiableModel
from django.core.exceptions import SuspiciousOperation
from django.contrib.auth.models import AnonymousUser

class SMSMessage(ModifiableModel):
    message_body = models.TextField()
    to_phone_number = models.CharField(verbose_name=_('Reserver phone number'), max_length=30, blank=True)
    berth_reservation = models.ForeignKey(BerthReservation, verbose_name=_('Reservation'), related_name='sms_messages', null=True, on_delete=models.SET_NULL)
    success = models.BooleanField(default=False)
    twilio_id = models.CharField(max_length=100, blank=True)