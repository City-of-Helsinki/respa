import django.contrib.postgres.fields as pgfields
from django.conf import settings
from django.contrib.gis.db import models
from django.utils.translation import ugettext_lazy as _
from psycopg2.extras import DateTimeTZRange

from .base import ModifiableModel
from .utils import get_dt, save_dt


class Reservation(ModifiableModel):
    resource = models.ForeignKey('Resource', verbose_name=_('Resource'), db_index=True, related_name='reservations')
    begin = models.DateTimeField(verbose_name=_('Begin time'))
    end = models.DateTimeField(verbose_name=_('End time'))
    duration = pgfields.DateTimeRangeField(verbose_name=_('Length of reservation'), null=True,
                                           blank=True, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('User'), null=True,
                             blank=True, db_index=True)

    def _save_dt(self, attr, dt):
        """
        Any DateTime object is converted to UTC time zone aware DateTime
        before save

        If there is no time zone on the object, resource's time zone will
        be assumed through its unit's time zone
        """
        save_dt(self, attr, dt, self.resource.unit.time_zone)

    def _get_dt(self, attr, tz):
        return get_dt(self, attr, tz)

    @property
    def begin_tz(self):
        return self.begin

    @begin_tz.setter
    def begin_tz(self, dt):
        self._save_dt('begin', dt)

    def get_begin_tz(self, tz):
        return self._get_dt("begin", tz)

    @property
    def end_tz(self):
        return self.end

    @end_tz.setter
    def end_tz(self, dt):
        """
        Any DateTime object is converted to UTC time zone aware DateTime
        before save

        If there is no time zone on the object, resource's time zone will
        be assumed through its unit's time zone
        """
        self._save_dt('end', dt)

    def get_end_tz(self, tz):
        return self._get_dt("end", tz)

    class Meta:
        verbose_name = _("reservation")
        verbose_name_plural = _("reservations")

    def __str__(self):
        return "%s -> %s: %s" % (self.begin, self.end, self.resource)

    def save(self, *args, **kwargs):
        self.begin, self.end = self.resource.get_reservation_period(self)
        if self.begin and self.end:
            self.duration = DateTimeTZRange(self.begin, self.end)
        return super(Reservation, self).save(*args, **kwargs)
