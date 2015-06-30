import datetime
from django.utils import timezone
from django.contrib.gis.db import models
from django.conf import settings
from django.utils.translation import ugettext as _
from django.core.exceptions import ValidationError
import django.db.models as dbm

DEFAULT_LANG = settings.LANGUAGES[0][0]


def get_translated(obj, attr):
    key = "%s_%s" % (attr, DEFAULT_LANG)
    val = getattr(obj, key, None)
    if not val:
        val = getattr(obj, attr)
    return val


class ModifiableModel(models.Model):
    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, related_name="%(class)s_created")
    modified_at = models.DateTimeField(default=timezone.now)
    modified_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, related_name="%(class)s_modified")

    class Meta:
        abstract = True


class Unit(ModifiableModel):
    id = models.CharField(primary_key=True, max_length=50)
    name = models.CharField(max_length=200)
    description = models.TextField(null=True)

    location = models.PointField(null=True, srid=settings.DEFAULT_SRID)
    # organization = models.ForeignKey(...)
    street_address = models.CharField(max_length=100, null=True)
    address_zip = models.CharField(max_length=10, null=True)
    phone = models.CharField(max_length=30, null=True)
    email = models.EmailField(max_length=100, null=True)
    www_url = models.URLField(max_length=400, null=True)
    address_postal_full = models.CharField(max_length=100, null=True)

    picture_url = models.URLField(max_length=200, null=True)
    picture_caption = models.CharField(max_length=200, null=True)

    class Meta:
        verbose_name = _("unit")
        verbose_name_plural = _("units")

    def __str__(self):
        return "%s (%s)" % (get_translated(self, 'name'), self.id)


class UnitIdentifier(models.Model):
    unit = models.ForeignKey(Unit, db_index=True, related_name='identifiers')
    namespace = models.CharField(max_length=50)
    value = models.CharField(max_length=100)

    class Meta:
        unique_together = (('namespace', 'value'), ('namespace', 'unit'))


class ResourceType(ModifiableModel):
    MAIN_TYPES = (
        ('space', _('Space')),
        ('person', _('Person')),
        ('item', _('Item'))
    )
    id = models.CharField(primary_key=True, max_length=100)
    main_type = models.CharField(max_length=20, choices=MAIN_TYPES)
    name = models.CharField(max_length=200)

    class Meta:
        verbose_name = _("resource type")
        verbose_name_plural = _("resource types")

    def __str__(self):
        return "%s (%s)" % (get_translated(self, 'name'), self.id)


class Resource(ModifiableModel):
    id = models.CharField(primary_key=True, max_length=100)
    unit = models.ForeignKey(Unit, db_index=True, null=True, blank=True, related_name="resources")
    type = models.ForeignKey(ResourceType, db_index=True)
    name = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    photo = models.URLField(null=True, blank=True)
    need_manual_confirmation = models.BooleanField(default=False)

    people_capacity = models.IntegerField(null=True, blank=True)
    area = models.IntegerField(null=True, blank=True)
    ground_plan = models.URLField(null=True, blank=True)

    # if not set, location is inherited from unit
    location = models.PointField(null=True, blank=True, srid=settings.DEFAULT_SRID)

    class Meta:
        verbose_name = _("resource")
        verbose_name_plural = _("resources")

    def __str__(self):
        return "%s (%s)/%s" % (get_translated(self, 'name'), self.id, self.unit)

    def get_opening_hours(self, begin, end=None):
        """
        Returns opening and closing time for a given date range

        If no end is not supplied or None, will return the opening hours
        as a dict. If end is given, returns all the opening hours for
        each day as a list.
        """

        if end is None:
            end = begin
            only_one = True
        else:
            only_one = False
        assert begin <= end
        if self.periods.exists():
            periods = self.periods
        else:
            periods = self.unit.periods

        periods = periods.filter(
            start__lte=begin, end__gte=end).annotate(
            length=dbm.F('end')-dbm.F('start')
        ).order_by('length')
        days = Day.objects.filter(period__in=periods)

        periods = list(periods)
        for period in periods:
            period.range_days = {day.weekday: day for day in days if day.period == period}

        date = begin
        date_list = []
        while date <= end:
            opens = None
            closes = None
            for period in periods:
                if period.start > date or period.end < date:
                    continue
                if period.closed:
                    break
                day = period.range_days.get(date.weekday())
                if day is None or day.closed:
                    break
                opens = day.opens
                closes = day.closes

            date_list.append({'date': date.isoformat(), 'opens': opens, 'closes': closes})
            date += datetime.timedelta(days=1)

        if only_one:
            return date_list[0]
        return date_list

    def get_open_from_now(self, dt):
        """
        Returns opening and closing for a given datetime starting from its moment
        and ends on closing time

        If no periods and days that contain given datetime are not found,
        returns none both
        """

        date, weekday, moment = dt.date(), dt.weekday(), dt.time()

        if self.periods.exists():
            periods = self.periods
        else:
            periods = self.unit.periods

        res = periods.filter(
            start__lte=date, end__gte=date).annotate(
            length=dbm.F('end')-dbm.F('start')
        ).order_by('length').first()

        if res:
            day = res.days.filter(weekday=weekday, opens__lte=moment, closes__gte=moment).first()
            if day:
                closes = dt.combine(dt, day.closes)
                return {'opens': moment, 'closes': closes}

        return {'opens': None, 'closes': None}


class Reservation(ModifiableModel):
    resource = models.ForeignKey(Resource, db_index=True, related_name='reservations')
    begin = models.DateTimeField()
    end = models.DateTimeField()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, db_index=True)

    class Meta:
        verbose_name = _("reservation")
        verbose_name_plural = _("reservations")

    def __str__(self):
        return "%s -> %s: %s" % (self.begin, self.end, self.resource)

    def save(self, *args, **kwargs):
        hours = self.resource.get_opening_hours(self.begin)
        if self.end.date() != self.begin.date():
            raise ValidationError(_("The reservation has to end on the same day"))
        if self.end <= self.begin:
            raise ValidationError(_("You must end the reservation after it has begun"))
        if self.begin.time() <= hours['opens']:
            raise ValidationError(_("You must start the reservation during opening hours"))
        if self.end.time() > hours['closes']:
            raise ValidationError(_("You must end the reservation before closing"))
        return super(Reservation, self).save(*args, **kwargs)


STATE_BOOLS = {False: _('open'), True: _('closed')}


class Period(models.Model):
    """
    A period of time to express state of open or closed
    Days that specifies the actual activity hours link here
    """
    resource = models.ForeignKey(Resource, db_index=True, null=True, blank=True,
                                 related_name='periods')
    unit = models.ForeignKey(Unit, db_index=True, null=True, blank=True,
                             related_name='periods')

    start = models.DateField()
    end = models.DateField()
    name = models.CharField(max_length=200)
    description = models.CharField(null=True, max_length=500)
    closed = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("period")
        verbose_name_plural = _("periods")

    def __str__(self):
        # FIXME: output date in locale-specific format
        return "{0}, {3}: {1:%d.%m.%Y} - {2:%d.%m.%Y}".format(self.name, self.start, self.end, STATE_BOOLS[self.closed])

    def save(self, *args, **kwargs):
        if (self.resource is not None and self.unit is not None) or \
           (self.resource is None and self.unit is None):
            raise ValidationError(_("You must set either 'resource' or 'unit', but not both"))
        return super(Period, self).save(*args, **kwargs)


class Day(models.Model):
    """
    Day of week and its active start and end time and whether it is open or closed

    Kirjastot.fi API uses closed for both days and periods, don't know which takes precedence
    """
    DAYS_OF_WEEK = (
        (0, _('Monday')),
        (1, _('Tuesday')),
        (2, _('Wednesday')),
        (3, _('Thursday')),
        (4, _('Friday')),
        (5, _('Saturday')),
        (6, _('Sunday'))
    )

    period = models.ForeignKey(Period, db_index=True, related_name='days')
    weekday = models.IntegerField("Day of week as a number 0-6", choices=DAYS_OF_WEEK)
    opens = models.TimeField("Clock as number, 0000 - 2359", null=True, blank=True)
    closes = models.TimeField("Clock as number, 0000 - 2359", null=True, blank=True)
    closed = models.NullBooleanField(default=False)  # NOTE: If this is true and the period is false, what then?

    class Meta:
        verbose_name = _("day")
        verbose_name_plural = _("days")

    def __str__(self):
        # FIXME: output date in locale-specific format
        return "{4}, {3}: {1:%d.%m.%Y} - {2:%d.%m.%Y}, {0}: {3}".format(
            self.get_weekday_display(), self.period.start, self.period.end, STATE_BOOLS[self.closed], self.period.name)
