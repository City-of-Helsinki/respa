from django.contrib.gis.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from resources.models import Reservation

class HMLReservation(models.Model):
    berth = models.ForeignKey('Berth', verbose_name=_('Berth'), db_index=True, related_name='hml_reservations', null=True)
    reservation = models.OneToOneField(Reservation, verbose_name=_('Reservation'), db_index=True, on_delete=models.CASCADE)
    is_paid = models.BooleanField(verbose_name=_('Is paid'), default=False)
    reserver_ssn = models.CharField(verbose_name=_('Reserver ssn'), default='', max_length=11)
    state_updated_at = models.DateTimeField(verbose_name=_('Time of modification'), default=timezone.now)
    is_paid_at = models.DateTimeField(verbose_name=_('Time of payment'), null=True, blank=True)
    key_returned = models.BooleanField(verbose_name=_('Key returned'), default=False)
    key_returned_at = models.DateTimeField(verbose_name=_('Time of key returned'), null=True, blank=True)