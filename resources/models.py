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
    created_at = models.DateTimeField(verbose_name=_('Time of creation'), default=timezone.now)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('Created by'),
                                   null=True, blank=True, related_name="%(class)s_created")
    modified_at = models.DateTimeField(verbose_name=_('Time of modification'), default=timezone.now)
    modified_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('Modified by'),
                                    null=True, blank=True, related_name="%(class)s_modified")

    class Meta:
        abstract = True


def get_opening_hours(periods, begin, end=None):
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
        ret = date_list[0]
        del ret['date']
        return ret
    return date_list


class Unit(ModifiableModel):
    id = models.CharField(primary_key=True, max_length=50)
    name = models.CharField(verbose_name=_('Name'), max_length=200)
    description = models.TextField(verbose_name=_('Description'), null=True, blank=True)

    location = models.PointField(verbose_name=_('Location'), null=True, srid=settings.DEFAULT_SRID)
    # organization = models.ForeignKey(...)
    street_address = models.CharField(verbose_name=_('Street address'), max_length=100, null=True)
    address_zip = models.CharField(verbose_name=_('Postal code'), max_length=10, null=True, blank=True)
    phone = models.CharField(verbose_name=_('Phone number'), max_length=30, null=True, blank=True)
    email = models.EmailField(verbose_name=_('Email'), max_length=100, null=True, blank=True)
    www_url = models.URLField(verbose_name=_('WWW link'), max_length=400, null=True, blank=True)
    address_postal_full = models.CharField(verbose_name=_('Full postal address'), max_length=100,
                                           null=True, blank=True)

    picture_url = models.URLField(verbose_name=_('Picture URL'), max_length=200,
                                  null=True, blank=True)
    picture_caption = models.CharField(verbose_name=_('Picture caption'), max_length=200,
                                       null=True, blank=True)

    class Meta:
        verbose_name = _("unit")
        verbose_name_plural = _("units")

    def __str__(self):
        return "%s (%s)" % (get_translated(self, 'name'), self.id)

    def get_opening_hours(self, begin=None, end=None):
        if begin is None:
            begin = datetime.date.today()
        periods = self.periods
        ret = get_opening_hours(periods, begin, end)
        return ret


class UnitIdentifier(models.Model):
    unit = models.ForeignKey(Unit, verbose_name=_('Unit'), db_index=True, related_name='identifiers')
    namespace = models.CharField(verbose_name=_('Namespace'), max_length=50)
    value = models.CharField(verbose_name=_('Value'), max_length=100)

    class Meta:
        unique_together = (('namespace', 'value'), ('namespace', 'unit'))


class ResourceType(ModifiableModel):
    MAIN_TYPES = (
        ('space', _('Space')),
        ('person', _('Person')),
        ('item', _('Item'))
    )
    id = models.CharField(primary_key=True, max_length=100)
    main_type = models.CharField(verbose_name=_('Main type'), max_length=20, choices=MAIN_TYPES)
    name = models.CharField(verbose_name=_('Name'), max_length=200)

    class Meta:
        verbose_name = _("resource type")
        verbose_name_plural = _("resource types")

    def __str__(self):
        return "%s (%s)" % (get_translated(self, 'name'), self.id)


class Resource(ModifiableModel):
    id = models.CharField(primary_key=True, max_length=100)
    unit = models.ForeignKey(Unit, verbose_name=_('Unit'), db_index=True, null=True, blank=True,
                             related_name="resources")
    type = models.ForeignKey(ResourceType, verbose_name=_('Resource type'), db_index=True)
    name = models.CharField(verbose_name=_('Name'), max_length=200)
    description = models.TextField(verbose_name=_('Description'), null=True, blank=True)
    photo = models.URLField(verbose_name=_('Photo URL'), null=True, blank=True)
    need_manual_confirmation = models.BooleanField(verbose_name=_('Need manual confirmation'), default=False)

    people_capacity = models.IntegerField(verbose_name=_('People capacity'), null=True, blank=True)
    area = models.IntegerField(verbose_name=_('Area'), null=True, blank=True)
    ground_plan = models.URLField(verbose_name=_('Ground plan URL'), null=True, blank=True)

    # if not set, location is inherited from unit
    location = models.PointField(verbose_name=_('Location'), null=True, blank=True, srid=settings.DEFAULT_SRID)

    class Meta:
        verbose_name = _("resource")
        verbose_name_plural = _("resources")

    def __str__(self):
        return "%s (%s)/%s" % (get_translated(self, 'name'), self.id, self.unit)

    def get_opening_hours(self, begin=None, end=None):
        if self.periods.exists():
            periods = self.periods
        else:
            periods = self.unit.periods

        if begin is None:
            begin = datetime.date.today()
        return get_opening_hours(periods, begin, end)

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
    resource = models.ForeignKey(Resource, verbose_name=_('Resource'), db_index=True, related_name='reservations')
    begin = models.DateTimeField(verbose_name=_('Begin time'))
    end = models.DateTimeField(verbose_name=_('End time'))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('User'), null=True,
                             blank=True, db_index=True)

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
    resource = models.ForeignKey(Resource, verbose_name=_('Resource'), db_index=True,
                                 null=True, blank=True, related_name='periods')
    unit = models.ForeignKey(Unit, verbose_name=_('Unit'), db_index=True,
                             null=True, blank=True, related_name='periods')

    start = models.DateField(verbose_name=_('Start date'))
    end = models.DateField(verbose_name=_('End date'))
    name = models.CharField(max_length=200, verbose_name=_('Name'))
    description = models.CharField(verbose_name=_('Description'), null=True,
                                   blank=True, max_length=500)
    closed = models.BooleanField(verbose_name=_('Closed'), default=False)

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

    period = models.ForeignKey(Period, verbose_name=_('Period'), db_index=True, related_name='days')
    weekday = models.IntegerField(verbose_name=_('Weekday'), choices=DAYS_OF_WEEK)
    opens = models.TimeField(verbose_name=_('Time when opens'), null=True, blank=True)
    closes = models.TimeField(verbose_name=_('Time when closes'), null=True, blank=True)
    closed = models.NullBooleanField(verbose_name=_('Closed'), default=False)  # NOTE: If this is true and the period is false, what then?

    class Meta:
        verbose_name = _("day")
        verbose_name_plural = _("days")

    def __str__(self):
        # FIXME: output date in locale-specific format
        return "{4}, {3}: {1:%d.%m.%Y} - {2:%d.%m.%Y}, {0}: {3}".format(
            self.get_weekday_display(), self.period.start, self.period.end, STATE_BOOLS[self.closed], self.period.name)
