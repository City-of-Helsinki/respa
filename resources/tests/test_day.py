import datetime
import pytest
import pytz
from dateutil import parser

from resources.models import Period, Day


@pytest.mark.django_db
def test_opening_hours(resource_in_unit):
    unit = resource_in_unit.unit
    # Regular hours for one week
    p1 = Period.objects.create(start=datetime.date(2015, 1, 1), end=datetime.date(2015, 12, 31),
                               unit=unit, name='regular hours')
    for weekday in range(0, 7):
        Day.objects.create(period=p1, weekday=weekday,
                           opens=datetime.time(8, 0),
                           closes=datetime.time(18, 0))

    # Two shorter days as exception
    exp1 = Period.objects.create(start=datetime.date(2015, 1, 10),
                                 end=datetime.date(2015, 1, 12),
                                 unit=unit, name='exceptionally short days')
    Day.objects.create(period=exp1, weekday=exp1.start.weekday(),
                       opens=datetime.time(12, 0), closes=datetime.time(14, 0))
    Day.objects.create(period=exp1, weekday=(exp1.start.weekday() + 1) % 7,
                       opens=datetime.time(12, 0), closes=datetime.time(14, 0))
    Day.objects.create(period=exp1, weekday=(exp1.start.weekday() + 2) % 7,
                       opens=datetime.time(12, 0), closes=datetime.time(14, 0))

    # Closed for one day
    exp2 = Period.objects.create(start=datetime.date(2015, 1, 15), end=datetime.date(2015, 8, 15),
                                 unit=unit, name='weekend is closed', closed=True)

    periods = Period.objects.all()
    assert len(periods) == 3

    tz = unit.get_tz()
    begin = tz.localize(datetime.datetime(2015, 1, 8))
    end = begin + datetime.timedelta(days=10)
    opening_hours = resource_in_unit.get_opening_hours(begin, end)

    def assert_hours(date_str, opens, closes=None):
        date = parser.parse(date_str).date()
        hours = opening_hours.get(date)
        assert hours is not None
        assert len(hours) == 1
        hours = hours[0]
        if opens:
            opens = tz.localize(datetime.datetime.combine(date, parser.parse(opens).time()))
            assert hours['opens'] == opens
        else:
            assert hours['opens'] is None
        if closes:
            closes = tz.localize(datetime.datetime.combine(date, parser.parse(closes).time()))
            assert hours['closes'] == closes
        else:
            assert hours['closes'] is None

    assert_hours('2015-01-08', '08:00', '18:00')
    assert_hours('2015-01-09', '08:00', '18:00')
    assert_hours('2015-01-10', '12:00', '14:00')
    assert_hours('2015-01-11', '12:00', '14:00')
    assert_hours('2015-01-12', '12:00', '14:00')
    assert_hours('2015-01-13', '08:00', '18:00')
    assert_hours('2015-01-15', None)
