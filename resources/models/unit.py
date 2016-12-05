import pytz
from django.conf import settings
from django.contrib.gis.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from autoslug import AutoSlugField

from .base import AutoIdentifiedModel, ModifiableModel
from .utils import create_reservable_before_datetime, get_translated, get_translated_name
from .availability import get_opening_hours

from munigeo.models import Municipality


class Unit(ModifiableModel, AutoIdentifiedModel):
    id = models.CharField(primary_key=True, max_length=50)
    name = models.CharField(verbose_name=_('Name'), max_length=200)
    description = models.TextField(verbose_name=_('Description'), null=True, blank=True)

    location = models.PointField(verbose_name=_('Location'), null=True, srid=settings.DEFAULT_SRID)
    time_zone = models.CharField(verbose_name=_('Time zone'), max_length=50,
                                 default=timezone.get_default_timezone().zone,
                                 choices=[(x, x) for x in pytz.all_timezones])

    # organization = models.ForeignKey(...)
    street_address = models.CharField(verbose_name=_('Street address'), max_length=100, null=True)
    address_zip = models.CharField(verbose_name=_('Postal code'), max_length=10, null=True, blank=True)
    phone = models.CharField(verbose_name=_('Phone number'), max_length=30, null=True, blank=True)
    email = models.EmailField(verbose_name=_('Email'), max_length=100, null=True, blank=True)
    www_url = models.URLField(verbose_name=_('WWW link'), max_length=400, null=True, blank=True)
    address_postal_full = models.CharField(verbose_name=_('Full postal address'), max_length=100,
                                           null=True, blank=True)
    municipality = models.ForeignKey(Municipality, null=True, blank=True, verbose_name=_('Municipality'))

    picture_url = models.URLField(verbose_name=_('Picture URL'), max_length=200,
                                  null=True, blank=True)
    picture_caption = models.CharField(verbose_name=_('Picture caption'), max_length=200,
                                       null=True, blank=True)

    slug = AutoSlugField(populate_from=get_translated_name, unique=True)
    reservable_days_in_advance = models.PositiveSmallIntegerField(verbose_name=_('Reservable days in advance'),
                                                                  null=True, blank=True)

    class Meta:
        verbose_name = _("unit")
        verbose_name_plural = _("units")
        permissions = (
            ('can_approve_reservation', _('Can approve reservation')),
            ('can_view_reservation_access_code', _('Can view reservation access code')),
        )
        ordering = ('name',)

    def __str__(self):
        return "%s (%s)" % (get_translated(self, 'name'), self.id)

    def get_opening_hours(self, begin=None, end=None):
        """
        :rtype : dict[str, list[dict[str, datetime.datetime]]]
        :type begin: datetime.date
        :type end: datetime.date
        """
        return get_opening_hours(self.time_zone, self.periods, begin, end)

    def get_tz(self):
        return pytz.timezone(self.time_zone)

    def get_reservable_before(self):
        return create_reservable_before_datetime(self.reservable_days_in_advance)

    def is_admin(self, user):
        # Currently all staff members are allowed to administrate
        # all units. Might be more finegrained in the future.
        return user.is_staff


class UnitIdentifier(models.Model):
    unit = models.ForeignKey('Unit', verbose_name=_('Unit'), db_index=True, related_name='identifiers')
    namespace = models.CharField(verbose_name=_('Namespace'), max_length=50)
    value = models.CharField(verbose_name=_('Value'), max_length=100)

    class Meta:
        verbose_name = _("unit identifier")
        verbose_name_plural = _("unit identifiers")
        unique_together = (('namespace', 'value'), ('namespace', 'unit'))
