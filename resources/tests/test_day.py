import datetime
from datetime import date
import pytest

from resources.models import Period, Day
from .utils import assert_hours


def daterange(start_date, end_date):
    for n in range((end_date - start_date).days):
        yield start_date
        start_date += datetime.timedelta(days=1)


@pytest.mark.django_db
def test_opening_hours(resource_in_unit):
    unit = resource_in_unit.unit
    tz = unit.get_tz()

    # Regular hours for the whole year
    p1 = Period.objects.create(start=date(2015, 1, 1), end=date(2015, 12, 31),
                               unit=unit, name='regular hours')
    for weekday in range(0, 7):
        Day.objects.create(period=p1, weekday=weekday,
                           opens=datetime.time(8, 0),
                           closes=datetime.time(18, 0))

    begin = tz.localize(datetime.datetime(2015, 6, 1))
    end = begin + datetime.timedelta(days=30)
    resource_in_unit.update_opening_hours()
    hours = resource_in_unit.get_opening_hours(begin, end)
    for d in daterange(date(2015, 6, 1), date(2015, 6, 7)):
        assert_hours(tz, hours, d, '08:00', '18:00')

    # Summer hours
    p2 = Period.objects.create(start=date(2015, 6, 1), end=date(2015, 9, 1),
                               unit=unit, name='summer hours')
    for weekday in range(0, 5):
        Day.objects.create(period=p2, weekday=weekday,
                           opens=datetime.time(10, 0),
                           closes=datetime.time(16, 0))
    Day.objects.create(period=p2, weekday=5, closed=True)
    Day.objects.create(period=p2, weekday=6, closed=True)

    resource_in_unit.update_opening_hours()
    hours = resource_in_unit.get_opening_hours(begin, end)
    assert_hours(tz, hours, date(2015, 6, 1), '10:00', '16:00')
    assert_hours(tz, hours, date(2015, 6, 2), '10:00', '16:00')
    assert_hours(tz, hours, date(2015, 6, 6), None)
    assert_hours(tz, hours, date(2015, 6, 7), None)

    # Closed June 9
    p3 = Period.objects.create(start=date(2015, 6, 9), end=date(2015, 6, 9),
                               unit=unit, name='closed june9')
    Day.objects.create(period=p3, weekday=1, closed=True)
    resource_in_unit.update_opening_hours()
    hours = resource_in_unit.get_opening_hours(begin, end)
    assert_hours(tz, hours, date(2015, 6, 8), '10:00', '16:00')
    assert_hours(tz, hours, date(2015, 6, 9), None)
    assert_hours(tz, hours, date(2015, 6, 10), '10:00', '16:00')

    # Re-opened the week of June 8
    p4 = Period.objects.create(start=date(2015, 6, 8), end=date(2015, 6, 14),
                               unit=unit, name='re-opened')
    for d in range(0, 7):
        Day.objects.create(period=p4, weekday=d, opens=datetime.time(12, 0), closes=datetime.time(14, 0))
    resource_in_unit.update_opening_hours()
    hours = resource_in_unit.get_opening_hours(begin, end)
    assert_hours(tz, hours, date(2015, 6, 8), '12:00', '14:00')
    assert_hours(tz, hours, date(2015, 6, 9), None)
    assert_hours(tz, hours, date(2015, 6, 10), '12:00', '14:00')

    # Dayless period; is closed
    Period.objects.create(start=date(2015, 6, 10), end=date(2015, 6, 14),
                          unit=unit, name='dayless')
    resource_in_unit.update_opening_hours()
    hours = resource_in_unit.get_opening_hours(begin, end)
    assert_hours(tz, hours, date(2015, 6, 10), None)
    assert_hours(tz, hours, date(2015, 6, 11), None)

    # Period that overlaps the parent but is not fully contained in it
    p6 = Period.objects.create(start=date(2014, 12, 30), end=date(2015, 1, 10),
                               unit=unit, name='overlapping')
    Day.objects.create(period=p6, weekday=1, opens=datetime.time(10, 0), closes=datetime.time(14, 0))
    Day.objects.create(period=p6, weekday=3, opens=datetime.time(10, 0), closes=datetime.time(14, 0))
    Day.objects.create(period=p6, weekday=4, opens=datetime.time(10, 0), closes=datetime.time(14, 0))

    begin = tz.localize(datetime.datetime(2014, 12, 29))
    end = begin + datetime.timedelta(days=30)
    resource_in_unit.update_opening_hours()
    hours = resource_in_unit.get_opening_hours(begin, end)
    assert_hours(tz, hours, date(2014, 12, 29), None)
    assert_hours(tz, hours, date(2014, 12, 30), '10:00', '14:00')
    assert_hours(tz, hours, date(2014, 12, 31), None)
    assert_hours(tz, hours, date(2015, 1, 1), '10:00', '14:00')
    assert_hours(tz, hours, date(2015, 1, 2), '10:00', '14:00')
    assert_hours(tz, hours, date(2015, 1, 3), None)
