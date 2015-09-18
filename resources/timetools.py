from .models import Day, Resource, Period, Unit, ResourceType, Reservation
from psycopg2.extras import DateTimeTZRange, DateRange, NumericRange
import datetime
import arrow
from collections import namedtuple
import django.db.models as djdbm
from django.utils import timezone
import pytz
from django.utils.dateformat import format, time_format

OpenHours = namedtuple("OpenHours", ['opens', 'closes'])


class TimeWarp(object):
    """
    A time handling helper class

    Give it datetime or date and optional end datetime or end date for ranges

    Get back time zone aware date times, but rely on calculations done using
     UTC and normalized to your chosen time zone

    Also supports time deltas, comparisons, date's start and end

    TODO: ambiguous DST times are not handled, though Pytz supports this
    """

    SERIALIZATION_FORMATS = {
        "finnish": "j.n.Y G.i"
    }

    def __init__(self, dt=None, day=None, end_dt=None, end_day=None, original_timezone=None):
        """
        Converts given dt or day into UTC date time object
        and saves this and the original time zone object
        into object's fields

        NOTE: At the moment Arror generated DateTime's will fail time zone conversion
        since Arrow does zone handling differently than Pytz, use Pytz zone localized
        or naive datetimes or state the original timezone explicitly

        :param dt: TimeWarp sole datetime or start of date time range
        :type dt: datetime.datetime | None
        :param day: a date of TimeWarp or start of date range
        :type day: datetime.date | None
        :param end_dt: end of date range
        :type end_dt: datetime.datetime | None
        :param end_day: end of date range
        :type end_day: datetime.date | None
        :param original_timezone: a string stating original time zone for dame
        :type original_timezone: basestring
        :rtype: TimeWarp
        """
        if dt and not hasattr(dt, "tzinfo"):
            raise ValueError(type(dt), "has no attribute tzinfo")

        self.dt = None
        self.end_dt = None
        self.dt_range = None
        self.as_date = False

        if day:
            self.original_timezone = pytz.utc
            self.dt = self._date_to_dt(day)
        elif dt:
            self.original_timezone = self.find_timezone(dt, original_timezone)
            self.dt = self.dt_as_utc(dt, self.original_timezone)
        else:
            # Now dates, well be the moment of creation
            self.original_timezone = timezone.get_current_timezone()
            self.dt = self.dt_as_utc(datetime.datetime.now(), self.original_timezone)

        if end_day:
            self.end_dt = self._date_to_dt(end_day)
        elif end_dt:
            self.end_dt = self.dt_as_utc(end_dt, self.original_timezone)

        if self.end_dt:
            if self.end_dt < self.dt:
                raise ValueError(self.dt, self.end_dt,
                                 "End range can't be earlier than start range")
            self.dt_range = DateTimeTZRange(self.dt, self.end_dt)
            self.as_date = True  # NOTE: created as date, which have no time zone

    def __repr__(self):
        return '<TimeWarp "{0}">'.format(
            ", ".join(str(i) for i in (
                self.dt, self.end_dt, self.original_timezone, self.as_date) if i)
        )

    def _date_to_dt(self, day):
        return self.dt_as_utc(datetime.datetime.combine(day, datetime.time(0, 0)),
                              self.original_timezone)

    def find_timezone(self, dt, original_timezone=None):
        """
        Gets the pytz time zone object from given original time zone,
        or uses datetime objects own
        or finally returns Django's current time zone

        :type dt: datetime.datetime
        :type original_timezone: string
        :rtype: pytz.timezone
        """
        if original_timezone:
            return pytz.timezone(original_timezone)
        elif dt.tzinfo and dt.tzinfo.zone:
            return pytz.timezone(dt.tzinfo.zone)
        else:
            return timezone.get_current_timezone()

    def dt_as_utc(self, dt, zone=None):
        """
        Normalizes given datetime to UTC

        DateTime with time zone cast to UTC
        Naive DateTime is in given time zone and is casted to UTC
        When no zone is given and DateTime is naive, localize it to UTC as is

        :param dt: datetime to normalize
        :type dt: datetime.datetime
        :param zone: a pytz time zone
        :type zone: pytz.timezone | None
        :return: datetime in UTC
        :rtype: pytz.timezone
        """
        if dt.tzinfo:
            return dt.astimezone(pytz.utc)
        elif zone:
            return zone.localize(dt).astimezone(pytz.utc)
        else:
            return pytz.utc.localize(dt)

    def get_delta(self, delta, operator, zone=None):
        """

        :param delta:
        :type delta: datetime.timedelta
        :param operator: operator function to apply
        :type operator: func
        :param zone:
        :type zone: pytz.timezone
        :return:
        :rtype: TimeWarp
        """
        if zone:
            return TimeWarp(operator(self.dt.astimezone(zone), delta))
        else:
            return TimeWarp(operator(self.dt.astimezone(self.original_timezone),
                                     delta))

    def __lt__(self, other):
        return self.dt <= other.dt

    def __gt__(self, other):
        return self.dt >= other.dt

    def __eq__(self, other):
        return self.dt == other.dt

    def __ne__(self, other):
        return self.dt != other.dt

    def astimezone(self, tz=None):
        if tz:
            return self.dt.astimezone(pytz.timezone(tz))
        else:
            return self.dt.astimezone(self.original_timezone)

    def ceiling(self):
        return TimeWarp(datetime.datetime.combine(self.dt.date(),
                                                  datetime.time(0,0)),
                        original_timezone=self.original_timezone.zone)

    def floor(self):
        dt = self.dt + datetime.timedelta(days=+1)
        return TimeWarp(self.dt.combine(dt.date(), datetime.time(0,0)),
                        original_timezone=self.original_timezone.zone)

    def serialize(self, dt_format=None, zone=None):
        """
        Serializes datetimes using given format or default format if None,
        in given or original time zone
        Returns formatted strings as dict for both datetime fields if present

        TimeWarp class now has built in time formats
        Serializer can use given format or you can choose from built in formats
        Builtin formats use Django's date formatter and argument format uses Python's own
        Also, datetimes are cast to given time zone or the
        original_timezone is used

        :param dt_format: a key in class formats or a Python format string
        :type dt_format: string
        :return: a dict with object's used datetime fields formatted
        :rtype: dict[string, string]
        """
        if not zone:
            zone = self.original_timezone
        else:
            zone = pytz.timezone(zone)
        resp = {}
        for key in ("dt", "end_dt"):
            field = getattr(self, key)
            if field:
                field = field.astimezone(zone)
                if not dt_format:
                    resp[key] = format(field, self.SERIALIZATION_FORMATS["finnish"])
                else:
                    try:
                        resp[key] = format(field, self.SERIALIZATION_FORMATS[dt_format])
                    except KeyError:
                        resp[key] = dt_format.format(field)
        return resp

def get_opening_hours(begin, end, resources=None):
    """
    :type begin:datetime.date
    :type end:datetime.date
    :type resources: Resource | None
    :rtype: dict[datetime, dict[Resource, list[OpenHours]]]

    Find opening hours for all resources on a given time period.

    If resources is None, finds opening hours for all resources.

    This version goes through all regular periods and then all
    exception periods that are found overlapping the given
    time range. It builds a dict of days that has dict of
    resources with their active hours.

    TODO: There is couple optimization avenues worth exploring
    with prefetch or select_related for Periods'
    relational fields Unit, Resource and Day. This way all
    relevant information could be requested with one or two
    queries from the db.
    """
    if not resources:
        resources = Resource.objects.all()

    if not begin < end:
        end = begin + datetime.timedelta(days=1)

    d_range = DateRange(begin, end)

    periods = Period.objects.filter(
        djdbm.Q(resource__in=resources) | djdbm.Q(unit__in=resources.values("unit__pk")),
        duration__overlap=d_range).order_by('exception')

    begin_dt = datetime.datetime.combine(begin, datetime.time(0, 0))
    end_dt = datetime.datetime.combine(end, datetime.time(0, 0))

    # Generates a dict of time range's days as keys and values as active period's days

    # all requested dates are assumed closed
    dates = {r.date() : False for r in arrow.Arrow.range('day', begin_dt, end_dt)}

    for period in periods:

        if period.start < begin:
            start = begin_dt
        else:
            start = arrow.get(period.start)
        if period.end > end:
            end = end_dt
        else:
            end = arrow.get(period.end)

        if period.resource:
            period_resources = [period.resource]
        else:
            period_resources = period.unit.resources.filter(pk__in=resources)

        for res in period_resources:

            for r in arrow.Arrow.range('day', start, end):
                for day in period.days.all():
                    if day.weekday is r.weekday():
                        if not dates.get(r.date(), None):
                            dates[r.date] = {}
                        dates[r.date()].setdefault(
                                res, []).append(
                            OpenHours(day.opens, day.closes))

    return dates

from django.db.models import Prefetch

def get_availability(begin, end, duration, resources):

    if not resources:
        resources = Resource.objects.all()

    d_range = DateRange(begin, end)

    # Saved query for overlapping periods, fetching also their Day items
    qs_periods = Period.objects.filter(
        duration__overlap=d_range
    ).order_by('exception').prefetch_related('days')

    # Saved query for Unit's overlapping periods, fetching also their Day items
    qs_unit_periods = Unit.objects.filter(
        periods__duration__overlap=d_range
    ).order_by('periods__exception').prefetch_related('periods__days')

    # Saved query for overlapping reservations
    qs_reservations = Reservation.objects.filter(duration__overlap=d_range)

    # Get all resources and prefetch to stated attributes to the items
    # their matching Period, Unit and Reservation
    # items according to queries defined above

    resources_during_time = resources.prefetch_related(
        Prefetch('periods', queryset=qs_periods, to_attr='overlapping_periods'),
        Prefetch('unit', queryset=qs_unit_periods, to_attr='overlapping_unit_periods'),
        Prefetch('reservations', queryset=qs_reservations, to_attr='overlapping_reservations')
    )

    # NOTE: Resource's Period overrides Unit's Period

    opening_hours = {}

    for res in resources:
        opening_hours[res] = periods_to_opening_hours(res, begin, end)


    """
    Loop through all Unit and Resource Periods and append their day states

    For Reservations, calculate the spaces between opening and closing time
    and between Reservations and add them to their own list of before and after
    time deltas

    Go through each day and flag all dates that can fit given duration

    Or just add Reservations and in doing so calculate their preceding space

    Should this fit given duration, flag the day, moving to next day's Reservations

    API can calculate all fitting slots, but is it necessary at this stage?
    """

def periods_to_opening_hours(resource, begin, end):
    """
    Goes through resource's unit's periods and its own
    periods

    Creates opening hours for each day

    First unit's regular days are processed, then their exceptions
    Then same order for resource itself

    Resulting date dict is union of all periodical information
    or false if given day is closed

    Also, all days that don't have a period are assumed closed

    :param resource:
    :type resource:
    :param begin:
    :type begin:
    :param end:
    :type end:
    :return:
    :rtype:
    """
    begin_dt = datetime.datetime.combine(begin, datetime.time(0, 0))
    end_dt = datetime.datetime.combine(end, datetime.time(0, 0))

    # Generates a dict of time range's days as keys and values as active period's days

    # all requested dates are assumed closed
    dates = {r.date() : False for r in arrow.Arrow.range('day', begin_dt, end_dt)}

    for period in resource.overlapping_unit_periods:
        if period.start < begin:
            start = begin_dt
        else:
            start = arrow.get(period.start)
        if period.end > end:
            end = end_dt
        else:
            end = arrow.get(period.end)

        for r in arrow.Arrow.range('day', start, end):
            for day in period.days.all():
                if day.weekday is r.weekday():
                    if day.closed:
                        dates[r.date()] = False
                    else:
                        dates[r.date()] = OpenHours(day.opens, day.closes)

    for period in resource.overlapping_periods:
        if period.start < begin:
            start = begin_dt
        else:
            start = arrow.get(period.start)
        if period.end > end:
            end = end_dt
        else:
            end = arrow.get(period.end)

        for r in arrow.Arrow.range('day', start, end):
            for day in period.days.all():
                if day.weekday is r.weekday():
                    if day.closed:
                        dates[r.date()] = False
                    else:
                        dates[r.date()] = OpenHours(day.opens, day.closes)
    return dates

def set():
    u1 = Unit.objects.create(name='Unit 1', id='unit_1')
    rt = ResourceType.objects.create(name='Type 1', id='type_1', main_type='space')
    Resource.objects.create(name='Resource 1a', id='r1a', unit=u1, type=rt)
    Resource.objects.create(name='Resource 1b', id='r1b', unit=u1, type=rt)
    Resource.objects.create(name='Resource 2a', id='r2a', unit=u1, type=rt)
    Resource.objects.create(name='Resource 2b', id='r2b', unit=u1, type=rt)

    # Regular hours for one week
    p1 = Period.objects.create(start=datetime.date(2015, 8, 3), end=datetime.date(2015, 8, 9),
                               unit=u1, name='regular hours')
    Day.objects.create(period=p1, weekday=0, opens=datetime.time(8, 0), closes=datetime.time(18, 0))
    Day.objects.create(period=p1, weekday=1, opens=datetime.time(8, 0), closes=datetime.time(18, 0))
    Day.objects.create(period=p1, weekday=2, opens=datetime.time(8, 0), closes=datetime.time(18, 0))
    Day.objects.create(period=p1, weekday=3, opens=datetime.time(8, 0), closes=datetime.time(18, 0))
    Day.objects.create(period=p1, weekday=4, opens=datetime.time(8, 0), closes=datetime.time(18, 0))
    Day.objects.create(period=p1, weekday=5, opens=datetime.time(12, 0), closes=datetime.time(16, 0))
    Day.objects.create(period=p1, weekday=6, opens=datetime.time(12, 0), closes=datetime.time(14, 0))

    # Two shorter days as exception
    exp1 = Period.objects.create(start=datetime.date(2015, 8, 6), end=datetime.date(2015, 8, 7),
                                 unit=u1, name='exceptionally short days', exception=True,
                                 parent=p1)
    Day.objects.create(period=exp1, weekday=3,
                       opens=datetime.time(12, 0), closes=datetime.time(14, 0))
    Day.objects.create(period=exp1, weekday=4,
                       opens=datetime.time(12, 0), closes=datetime.time(14, 0))

    # Weekend is closed as an exception
    exp2 = Period.objects.create(start=datetime.date(2015, 8, 8), end=datetime.date(2015, 8, 9),
                                 unit=u1, name='weekend is closed', closed=True, exception=True,
                                 parent=p1)

