from .models import Day, Resource, Period, Unit, ResourceType
from psycopg2.extras import DateTimeTZRange, DateRange, NumericRange
import datetime
import arrow
from collections import namedtuple
import django.db.models as djdbm
from django.utils import timezone
import pytz

OpenHours = namedtuple("OpenHours", ['opens', 'closes'])


class TimeWarp(object):

    def __init__(self, dt=None, day=None, end_dt=None, end_day=None, original_timezone=None):
        """
        Converts given dt or day into UTC date time object
        and saves this and the original time zone object
        into object's fields

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
        if day:
            self.original_timezone = pytz.utc
            self.dt = self._date_to_dt(day)
            self.date = day
        elif dt:
            self.original_timezone = self.find_timezone(dt, original_timezone)
            self.dt = self.normalize(dt, self.original_timezone)
        else:
            # Now dates, well be the moment of creation
            self.dt = self.normalize(datetime.datetime.now(), pytz.utc)
            self.original_timezone = pytz.utc
        


    def _date_to_dt(self, day):
        return self.normalize(datetime.datetime.combine(day, datetime.time(0, 0)),
                              self.original_timezone)

    def find_timezone(self, dt, original_timezone=None):
        if original_timezone:
            return pytz.timezone(original_timezone)
        elif dt.tzinfo:
            return dt.tzinfo
        else:
            return timezone.get_current_timezone()

    def normalize(self, dt, zone=None):
        """
        :param dt: datetime to normalize
        :type dt: datetime.datetime
        :param zone: a pytz time zone
        :type zone: pytz.timezone
        :param original_timezone: Name of original time zone
        :type original_timezone: string
        :return: Updates object in place
        :rtype: pytz.timezone
        """
        if zone:
            return zone.normalize(dt)
        else:
            return pytz.utc.normalize(dt)

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

