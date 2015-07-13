import struct
import base64
import time
import datetime
import pytz
from django.utils import timezone
from django.contrib.gis.db import models
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils.dateformat import time_format
import django.db.models as dbm
import django.contrib.postgres.fields as pgfields
from psycopg2.extras import DateTimeTZRange, DateRange, NumericRange
from django.utils import timezone

import arrow

DEFAULT_LANG = settings.LANGUAGES[0][0]

def save_dt(obj, attr, dt, orig_tz="UTC"):
    """
    Sets given field in an object to a DateTime object with or without
    a time zone converted into UTC time zone from given time zone

    If there is no time zone on the given DateTime, orig_tz will be used
    """
    if dt.tzinfo:
        arr = arrow.get(dt).to("UTC")
    else:
        arr = arrow.get(dt, orig_tz).to("UTC")
    setattr(obj, attr, arr.datetime)

def get_dt(obj, attr, tz):
    return arrow.get(getattr(obj, attr)).to(tz).datetime

def get_translated(obj, attr):
    key = "%s_%s" % (attr, DEFAULT_LANG)
    val = getattr(obj, key, None)
    if not val:
        val = getattr(obj, attr)
    return val


def generate_id():
    t = time.time() * 1000000
    b = base64.b32encode(struct.pack(">Q", int(t)).lstrip(b'\x00')).strip(b'=').lower()
    return b.decode('utf8')

def time_to_dtz(time, date=None, arr=None):
    tz = timezone.get_current_timezone()
    if time:
        if date:
            return tz.localize(datetime.datetime.combine(date, time))
        elif arr:
            return tz.localize(datetime.datetime(arr.year, arr.month, arr.day, time.hour, time.minute))
    else:
        return None


class AutoIdentifiedModel(models.Model):

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = generate_id()
        super().save(*args, **kwargs)

    class Meta:
        abstract = True


class ModifiableModel(models.Model):
    created_at = models.DateTimeField(verbose_name=_('Time of creation'), default=timezone.now)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('Created by'),
                                   null=True, blank=True, related_name="%(class)s_created")
    modified_at = models.DateTimeField(verbose_name=_('Time of modification'), default=timezone.now)
    modified_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('Modified by'),
                                    null=True, blank=True, related_name="%(class)s_modified")

    class Meta:
        abstract = True


def get_opening_hours_old(periods, begin, end=None, tzinfo=None):
    """
    Returns opening and closing time for a given date range

    If no end is not supplied or None, will return the opening hours
    as a dict. If end is given, returns all the opening hours for
    each day as a list. If tzinfo is not None, will return opening
    hours as datetime instances with the given timezone.
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

            if tzinfo:
                opens = datetime.datetime.combine(date, opens)
                closes = datetime.datetime.combine(date, closes)
                opens = tzinfo.localize(opens)
                closes = tzinfo.localize(closes)

        date_list.append({'date': date.isoformat(), 'opens': opens, 'closes': closes})
        date += datetime.timedelta(days=1)

    if only_one:
        ret = date_list[0]
        del ret['date']
        return ret
    return date_list

def get_opening_hours(periods, begin, end=None):
    """
    Returns opening and closing times for a given date range

    Return value is a dict where keys are days on the range
        and values are a list of Day objects for that day's active period
        containing opening and closing hours
    """
    if end:
        assert begin <= end

    periods = periods.filter(start__lte=begin, end__gte=end).order_by('start', 'end')
    days = Day.objects.filter(period__in=periods)

    for period in periods:
        period.range_days = [day for day in days if day.period == period]

    periods = {per: (exper for exper in periods if per.exception and exper.parent == per)
               for per in periods if not per.exception}

    begin_dt = datetime.datetime.combine(begin, datetime.time(0, 0))
    if end:
        end_dt = datetime.datetime.combine(end, datetime.time(0, 0))
    else:
        end_dt = begin_dt

    # Generates a dict of time range's days as keys and values as active period's days
    dates = {}
    for period, exception_periods in periods.items():

        # Date range for periods needs to be given start and end days, but other periods get to keep their range
        if period.start < begin_dt.date():
            start = begin_dt
        else:
            start = arrow.get(period.start)
        if period.end > end_dt.date():
            end = end_dt
        else:
            end = arrow.get(period.end)

        # For one period, generate all of its days and for given day, put its hours into the dict
        for r in arrow.Arrow.range('day', start, end):
            dates[r.date()] = [{'opens' : time_to_dtz(day.opens, arr=r),
                                'closes' : time_to_dtz(day.closes, arr=r)}
                        for day in period.range_days
                        if day.weekday is r.weekday()]

        if exception_periods:
            # For period's exceptional periods, generate a new dict for those days
            exception_dates = {}
            for exception_period in exception_periods:
                # Exceptions happen inside date range of their periods so same mulling of start and end days occur
                if period.start < begin_dt.date():
                    start = begin_dt
                else:
                    start = arrow.get(period.start)
                if period.end > end_dt.date():
                    end = end_dt
                else:
                    end = arrow.get(period.end)

                # Updating dict of exceptional dates with current exception period's days
                for r in arrow.Arrow.range('day', start, end):
                    exception_dates[r.date()] = [{'opens' : time_to_dtz(day.opens, arr=r),
                                                  'closes' : time_to_dtz(day.closes, arr=r)}
                                          for day in exception_period.range_days
                                          if day.weekday is r.weekday()]

            # And override full day list with exceptions where applicable
            dates.update(exception_dates)

    # Old format for memory, does not quite cut it for resources with intermittent open/closed periods during one day
    # These would be places that close for lunch, for instance
    # date_list.append({'date': date.isoformat(), 'opens': opens, 'closes': closes})

    return dates

class Unit(ModifiableModel, AutoIdentifiedModel):
    id = models.CharField(primary_key=True, max_length=50)
    name = models.CharField(verbose_name=_('Name'), max_length=200)
    description = models.TextField(verbose_name=_('Description'), null=True, blank=True)

    location = models.PointField(verbose_name=_('Location'), null=True, srid=settings.DEFAULT_SRID)
    time_zone = models.CharField(verbose_name=_('Time zone'), max_length=50, default=timezone.get_default_timezone().zone,
                                 choices=[(x, x) for x in pytz.all_timezones])

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
        today = arrow.get()
        if begin is None:
            begin = today.replace().floor('day').datetime
        if end is None:
            end = today.replace(days=+1).floor('day').datetime
        periods = self.periods
        return get_opening_hours(periods, begin, end)


class UnitIdentifier(models.Model):
    unit = models.ForeignKey(Unit, verbose_name=_('Unit'), db_index=True, related_name='identifiers')
    namespace = models.CharField(verbose_name=_('Namespace'), max_length=50)
    value = models.CharField(verbose_name=_('Value'), max_length=100)

    class Meta:
        unique_together = (('namespace', 'value'), ('namespace', 'unit'))


class ResourceType(ModifiableModel, AutoIdentifiedModel):
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


class Purpose(ModifiableModel):
    MAIN_TYPES = (
        ('audiovisual_work', _('Audiovisual work')),
        ('manufacturing', _('Manufacturing')),
        ('watch_and_listen', _('Watch and listen')),
        ('meet_and_work', _('Meet and work')),
        ('games', _('Games')),
        ('events_and_exhibitions', _('Events and exhibitions'))
    )
    id = models.CharField(primary_key=True, max_length=100)
    main_type = models.CharField(verbose_name=_('Main type'), max_length=40, choices=MAIN_TYPES)
    name = models.CharField(verbose_name=_('Name'), max_length=200)

    class Meta:
        verbose_name = _("resource type")
        verbose_name_plural = _("resource types")

    def __str__(self):
        return "%s (%s)" % (get_translated(self, 'name'), self.id)


class Resource(ModifiableModel, AutoIdentifiedModel):
    AUTHENTICATION_TYPES = (
        ('none', _('None')),
        ('weak', _('Weak')),
        ('strong', _('Strong'))
    )
    id = models.CharField(primary_key=True, max_length=100)
    unit = models.ForeignKey(Unit, verbose_name=_('Unit'), db_index=True, null=True, blank=True,
                             related_name="resources")
    type = models.ForeignKey(ResourceType, verbose_name=_('Resource type'), db_index=True)
    purposes = models.ManyToManyField(Purpose)
    name = models.CharField(verbose_name=_('Name'), max_length=200)
    description = models.TextField(verbose_name=_('Description'), null=True, blank=True)
    photo = models.URLField(verbose_name=_('Photo URL'), null=True, blank=True)
    need_manual_confirmation = models.BooleanField(verbose_name=_('Need manual confirmation'), default=False)
    authentication = models.CharField(blank=False, max_length=20, choices=AUTHENTICATION_TYPES)
    people_capacity = models.IntegerField(verbose_name=_('People capacity'), null=True, blank=True)
    area = models.IntegerField(verbose_name=_('Area'), null=True, blank=True)
    ground_plan = models.URLField(verbose_name=_('Ground plan URL'), null=True, blank=True)

    # if not set, location is inherited from unit
    location = models.PointField(verbose_name=_('Location'), null=True, blank=True, srid=settings.DEFAULT_SRID)

    min_period = models.DurationField(verbose_name=_('Minimum reservation time'), default=datetime.timedelta(minutes=30))
    max_period = models.DurationField(verbose_name=_('Maximum reservation time'), null=True, blank=True)

    class Meta:
        verbose_name = _("resource")
        verbose_name_plural = _("resources")

    def __str__(self):
        return "%s (%s)/%s" % (get_translated(self, 'name'), self.id, self.unit)

    def get_reservation_period(self, reservation):
        """
        Returns accepted start and end times for a suggested reservation

        If the reservation cannot be accepted, raises a ValidationError.
        """

        begin = reservation.begin
        end = reservation.end

        days = self.get_opening_hours(begin.date(), end.date())
        if not days.values():
            raise ValidationError(_("No hours for reservation period"))
        for n, day in enumerate(days.values()):
            for m, hours in enumerate(day):
                opening = hours['opens']
                closing = hours['closes']
                try:
                    if end <= begin:
                        raise ValidationError(_("You must end the reservation after it has begun"))
                    if opening is None or begin < opening:
                        raise ValidationError(_("You must start the reservation during opening hours"))
                    if end > closing:
                        raise ValidationError(_("You must end the reservation before closing"))
                    time_since_opening = datetime.timedelta(hours=begin.time().hour-opening.time().hour,
                                                            minutes=begin.time().minute-opening.time().minute,
                                                            seconds=begin.time().second-opening.time().second)
                    # We round down to the start of the time slot
                    time_slots_since_opening = int(time_since_opening/self.min_period)
                    begin = opening+(time_slots_since_opening*self.min_period)
                    # Duration is calculated modulo time slot
                    duration_in_slots = int((end-begin)/self.min_period)
                    if duration_in_slots <= 0:
                        raise ValidationError(_("The minimum duration for a reservation is "+str(self.min_period)))
                    if self.max_period:
                        if duration_in_slots > self.max_period/self.min_period:
                            raise ValidationError(_("The maximum reservation length is "+str(self.max_period)))
                    duration = duration_in_slots*self.min_period
                    end = begin+duration
                    if not self.is_available(begin, end, reservation):
                        raise ValidationError(_("The resource is already reserved for some of the period"))
                    return begin, end
                except ValidationError as e:
                    if n + 1 == len(days) and m + 1 == len(day):
                        # Last of days, no valid opening hours are found
                        raise e
                    else:
                        pass # other day might work better

    def is_available(self, begin, end, reservation=None):
        """
        Returns whether the resource is available between the two datetimes

        Will also return true when the resource is closed, if it is not reserved.
        The optional reservation argument is for disregarding a given
        reservation.
        """
        hours = self.get_available_hours(begin, end, reservation=reservation)
        if hours:
            if begin == hours[0]['starts'] and end == hours[0]['ends']:
                return True
        return False

    def get_available_hours(self, start=None, end=None, duration=None, reservation=None):
        """
        Returns hours that the resource is not reserved for a given date range

        Will also return hours when the resource is closed, if it is not reserved.
        This is so that admins can book resources during closing hours. Returns
        the available hours as a list of dicts. The optional reservation argument
        is for disregarding a given reservation during checking, if we wish to
        move an existing reservation. The optional duration argument specifies
        minimum length for periods to be returned.
        """
        today = arrow.get(timezone.now())
        if start is None:
            start = today.floor('day').naive
        if end is None:
            end = today.replace(days=+1).floor('day').naive
        tz = timezone.get_current_timezone()
        start = tz.localize(start)
        end = tz.localize(end)
        reservations = self.reservations.filter(
            end__gte=start, begin__lte=end).order_by('begin')
        hours_list = [({'starts': start})]
        first_checked = False
        for res in reservations:
            # skip the reservation that is being edited
            if res == reservation:
                continue
            # check if the reservation spans the beginning
            if not first_checked:
                first_checked = True
                if res.begin < start:
                    if res.end > end:
                        return []
                    hours_list[0]['starts'] = res.end
                    # proceed to the next reservation
                    continue
            if duration:
                if res.begin-hours_list[-1]['starts'] < duration:
                    # the free period is too short
                    continue
            hours_list[-1]['ends'] = timezone.localtime(res.begin)
            # check if the reservation spans the end
            if res.end > end:
                return hours_list
            hours_list.append({'starts': timezone.localtime(res.end)})
        if duration:
            if end-hours_list[-1]['starts'] < duration:
                # the free period is too short
                hours_list.pop()
                return hours_list
        hours_list[-1]['ends'] = end
        return hours_list

    def get_opening_hours(self, begin=None, end=None):
        if self.periods.exists():
            periods = self.periods
        else:
            periods = self.unit.periods

        today = arrow.get()
        if begin is None:
            begin = today.floor('day').datetime
        if end is None:
            end = begin # today.replace(days=+1).floor('day').datetime
        print(begin, end)
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
        #self.begin, self.end = self.resource.get_reservation_period(self)
        if self.begin and self.end:
            self.duration = DateTimeTZRange(self.begin, self.end)
        return super(Reservation, self).save(*args, **kwargs)


STATE_BOOLS = {False: _('open'), True: _('closed')}


class Period(models.Model):
    """
    A period of time to express state of open or closed
    Days that specifies the actual activity hours link here
    """
    parent = models.ForeignKey('Period', verbose_name=_('period'), null=True, blank=True)
    exception = models.BooleanField(verbose_name=_('Exceptional period'), default=False)
    resource = models.ForeignKey(Resource, verbose_name=_('Resource'), db_index=True,
                                 null=True, blank=True, related_name='periods')
    unit = models.ForeignKey(Unit, verbose_name=_('Unit'), db_index=True,
                             null=True, blank=True, related_name='periods')

    start = models.DateField(verbose_name=_('Start date'))
    end = models.DateField(verbose_name=_('End date'))
    duration = pgfields.DateRangeField(verbose_name=_('Length of period'), null=True,
                                       blank=True, db_index=True)

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
        if self.start and self.end:
            if self.start == self.end:
                # Range of 1 day must end on next day
                self.duration = DateRange(self.start,
                                          self.end + datetime.timedelta(days=+1))
            else:
                self.duration = DateRange(self.start, self.end)
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
    length = pgfields.IntegerRangeField(verbose_name=_('Range between opens and closes'), null=True,
                                          blank=True, db_index=True)
    # NOTE: If this is true and the period is false, what then?
    closed = models.NullBooleanField(verbose_name=_('Closed'), default=False)
    description = models.CharField(max_length=200, verbose_name=_('description'), null=True, blank=True)

    class Meta:
        verbose_name = _("day")
        verbose_name_plural = _("days")

    def __str__(self):
        # FIXME: output date in locale-specific format
        if self.opens and self.closes:
            hours = ", {0} - {1}".format(time_format(self.opens, "G:i"), time_format(self.closes, "G:i"))
        else:
            hours = ""
        return "{4}, {3}: {1:%d.%m.%Y} - {2:%d.%m.%Y}, {0}: {3} {5}".format(
            self.get_weekday_display(), self.period.start, self.period.end,
            STATE_BOOLS[self.closed], self.period.name, hours)

    def save(self, *args, **kwargs):
        if self.opens and self.closes:
            try:
                opens = int(self.opens.isoformat().replace(":", ""))
                closes = int(self.closes.isoformat().replace(":", ""))
            except AttributeError:
                opens = int(self.opens.replace(":", ""))
                closes = int(self.closes.replace(":", ""))
            self.length = NumericRange(opens, closes)
        return super(Day, self).save(*args, **kwargs)

