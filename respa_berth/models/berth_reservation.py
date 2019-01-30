from django.contrib.gis.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from resources.models import Reservation
from respa_berth.models.berth import Berth
import hashlib
import time

class BerthReservation(models.Model):
    berth = models.ForeignKey('Berth', verbose_name=_('Berth'), db_index=True, related_name='berth_reservations', null=True, on_delete=models.SET_NULL)
    reservation = models.OneToOneField(Reservation, verbose_name=_('Reservation'), db_index=True, on_delete=models.CASCADE, related_name='berth_reservation')
    is_paid = models.BooleanField(verbose_name=_('Is paid'), default=False)
    reserver_ssn = models.CharField(verbose_name=_('Reserver ssn'), blank=True, default='', max_length=11)
    state_updated_at = models.DateTimeField(verbose_name=_('Time of modification'), blank=True, null=True)
    is_paid_at = models.DateTimeField(verbose_name=_('Time of payment'), null=True, blank=True)
    key_returned = models.BooleanField(verbose_name=_('Key returned'), default=False)
    key_returned_at = models.DateTimeField(verbose_name=_('Time of key returned'), null=True, blank=True)
    renewal_code = models.CharField(verbose_name=_('Renewal code'), max_length=40, blank=True, null=True, default=None)
    parent = models.ForeignKey('self', blank=True, null=True, related_name='child')
    renewal_notification_month_sent_at = models.DateTimeField(verbose_name=_('Renewal notification month before end sent at'), blank=True, null=True)
    renewal_notification_week_sent_at = models.DateTimeField(verbose_name=_('Renewal notification week before end sent at'), blank=True, null=True)
    renewal_notification_day_sent_at = models.DateTimeField(verbose_name=_('Renewal notification day before end sent at'), blank=True, null=True)
    end_notification_sent_at = models.DateTimeField(verbose_name=_('End notification sent at'), blank=True, null=True)
    key_return_notification_sent_at = models.DateTimeField(verbose_name=_('Key return notification sent at'), blank=True, null=True)

    def set_paid(self, paid=True):
        if paid:
            self.is_paid = True
            self.is_paid_at = timezone.now()
        else:
            self.is_paid = False
            self.is_paid_at = None

        self.save()

    def set_renewal_code(self):
        code = hashlib.sha1(str(time.time()).encode('utf-8') + str(self.pk).encode('utf-8')).hexdigest()
        self.renewal_code = code
        self.save()
        return code

    def unset_renewal_code(self):
        self.renewal_code = None
        self.save()

    def get_payment_contact_data(self):
        first_name = ''
        last_name = ''
        name_separated = self.reservation.reserver_name.split(' ')
        if len(name_separated) >= 2:
            first_name = name_separated[0]
            last_name = name_separated[1]
        else:
            first_name = self.reservation.reserver_name
            last_name = self.reservation.reserver_name

        return {
            'telephone': self.reservation.reserver_phone_number,
            'mobile': self.reservation.reserver_phone_number,
            'email': self.reservation.reserver_email_address,
            'first_name': first_name,
            'last_name': last_name,
            'company': '',
            'street': self.reservation.reserver_address_street,
            'postal_code': self.reservation.reserver_address_zip,
            'postal_office': self.reservation.reserver_address_city,
            'country': 'FI',
        }

    def get_payment_product_data(self):
        berth_type = ''
        if self.berth.type == 'dock':
            berth_type = 'LAITURI'
        elif self.berth.type == 'ground':
            berth_type = 'POLETTI'
        elif self.berth.type == 'number':
            berth_type = 'NUMERO'
        else:
            raise Exception('Invalid or no berth type defined in %s' % s)
        return {
            'title': self.berth.resource.name + ' (' + self.berth.resource.unit.name + ')',
            'product_id': self.berth.id,
            'amount': 1,
            'price': str(self.berth.price),
            'vat': 24,
            'discount': 0,
            'type': 1,
            'berth_type': berth_type,
        }

    def cancel_reservation(self, user):
        if self.reservation.state != Reservation.CANCELLED:
            self.reservation.set_state(Reservation.CANCELLED, user)
            self.state_updated_at = timezone.now()
            self.parent = None
            self.save()
            if self.berth.type == Berth.GROUND:
                self.berth.is_disabled = True
                self.berth.save()
            else:
                resource = self.reservation.resource
                if not BerthReservation.objects.filter(berth=self.berth, reservation__end__gte=timezone.now(), reservation__state=Reservation.CONFIRMED).exists():
                    resource.reservable = True
                    resource.save()

    def __str__(self):
        return "%s - %s - %s" % (self.pk, self.reservation.reserver_name, self.berth.resource.name)
