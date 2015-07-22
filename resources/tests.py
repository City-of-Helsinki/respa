import pytz
import datetime
import arrow
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.test import TestCase
from .models import *


class DayTestCase(TestCase):
    """
    # Test case for day handler

    Creates a week of regular period with open hours and two day closed exceptional period

    Tests that day creation works as it should
    """

    def setUp(self):
        u1 = Unit.objects.create(name='Unit 1', id='unit_1')
        u2 = Unit.objects.create(name='Unit 2', id='unit_2')
        rt = ResourceType.objects.create(name='Type 1', id='type_1', main_type='space')
        Resource.objects.create(name='Resource 1a', id='r1a', unit=u1, type=rt)
        Resource.objects.create(name='Resource 1b', id='r1b', unit=u1, type=rt)
        Resource.objects.create(name='Resource 2a', id='r2a', unit=u2, type=rt)
        Resource.objects.create(name='Resource 2b', id='r2b', unit=u2, type=rt)

        # Regular hours for one week
        p1 = Period.objects.create(start=datetime.date(2015, 8, 3), end=datetime.date(2015, 8, 9), unit=u1, name='regular hours')
        Day.objects.create(period=p1, weekday=0, opens=datetime.time(8, 0), closes=datetime.time(18, 0))
        Day.objects.create(period=p1, weekday=1, opens=datetime.time(8, 0), closes=datetime.time(18, 0))
        Day.objects.create(period=p1, weekday=2, opens=datetime.time(8, 0), closes=datetime.time(18, 0))
        Day.objects.create(period=p1, weekday=3, opens=datetime.time(8, 0), closes=datetime.time(18, 0))
        Day.objects.create(period=p1, weekday=4, opens=datetime.time(8, 0), closes=datetime.time(18, 0))
        Day.objects.create(period=p1, weekday=5, opens=datetime.time(12, 0), closes=datetime.time(16, 0))
        Day.objects.create(period=p1, weekday=6, opens=datetime.time(12, 0), closes=datetime.time(14, 0))

        # Two shorter days as exception
        exp1 = Period.objects.create(start=datetime.date(2015, 8, 6), end=datetime.date(2015, 8, 7), unit=u1,
                                     name='exceptionally short days', exception=True, parent=p1)
        Day.objects.create(period=exp1, weekday=3,
                           opens=datetime.time(12, 0), closes=datetime.time(14, 0))
        Day.objects.create(period=exp1, weekday=4,
                           opens=datetime.time(12, 0), closes=datetime.time(14, 0))

        # Weekend is closed as an exception
        exp2 = Period.objects.create(start=datetime.date(2015, 8, 8), end=datetime.date(2015, 8, 9), unit=u1,
            name='weekend is closed', closed=True, exception=True, parent=p1)

    def test_days(self):
        periods = Period.objects.all()
        self.assertEqual(len(periods), 3)


class TimeTestCase:

    def setUp(self):
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

    def test_periods(self):
        from .timetools import get_opening_hours
        hours = get_opening_hours(datetime.date(2015,8,1), datetime.date(2015,8,10))


class ReservationTestCase(TestCase):

    def setUp(self):
        u1 = Unit.objects.create(name='Unit 1', id='unit_1', time_zone='Europe/Helsinki')
        u2 = Unit.objects.create(name='Unit 2', id='unit_2', time_zone='Europe/Helsinki')
        rt = ResourceType.objects.create(name='Type 1', id='type_1', main_type='space')
        Resource.objects.create(name='Resource 1a', id='r1a', unit=u1, type=rt)
        Resource.objects.create(name='Resource 1b', id='r1b', unit=u1, type=rt)
        Resource.objects.create(name='Resource 2a', id='r2a', unit=u2, type=rt)
        Resource.objects.create(name='Resource 2b', id='r2b', unit=u2, type=rt)

        p1 = Period.objects.create(start='2015-06-01', end='2015-09-01', unit=u1, name='')
        p2 = Period.objects.create(start='2015-06-01', end='2015-09-01', unit=u2, name='')
        p3 = Period.objects.create(start='2015-06-01', end='2015-09-01', resource_id='r1a', name='')
        Day.objects.create(period=p1, weekday=0, opens='08:00', closes='22:00')
        Day.objects.create(period=p2, weekday=1, opens='08:00', closes='16:00')
        Day.objects.create(period=p3, weekday=0, opens='08:00', closes='18:00')

    def test_opening_hours(self):
        r1a = Resource.objects.get(id='r1a')
        r1b = Resource.objects.get(id='r1b')

        date = arrow.get('2015-06-01').date()
        end = arrow.get('2015-06-02').date()
        days = r1a.get_opening_hours(begin=date, end=end)  # Monday
        hours = days[date][0] # first day object of chosen days
        self.assertEqual(hours['opens'].time(), datetime.time(8, 00))
        self.assertEqual(hours['closes'].time(), datetime.time(18, 00))

        days = r1b.get_opening_hours(begin=date, end=end)  # Monday
        hours = days[date][0] # first day object of chosen days
        self.assertEqual(hours['opens'].time(), datetime.time(8, 00))
        self.assertEqual(hours['closes'].time(), datetime.time(22, 00))

    def test_reservation(self):
        r1a = Resource.objects.get(id='r1a')
        r1b = Resource.objects.get(id='r1b')

        tz = timezone.get_current_timezone()
        begin = tz.localize(datetime.datetime(2015, 6, 1, 8, 0, 0))
        end = begin + datetime.timedelta(hours=2)

        Reservation.objects.create(resource=r1a, begin=begin, end=end)

        print(Reservation.objects.all())
        # Attempt overlapping reservation
        with self.assertRaises(ValidationError):
            Reservation.objects.create(resource=r1a, begin=begin,
                                       end=end)

        # Attempt reservation that starts before the resource opens
        with self.assertRaises(ValidationError):
            Reservation.objects.create(resource=r1a,
                                       begin=begin - datetime.timedelta(hours=1),
                                       end=end)

        begin = tz.localize(datetime.datetime(2015, 6, 1, 16, 0, 0))
        end = begin + datetime.timedelta(hours=2)

        print("debug", begin.isoformat(), end.isoformat())

        # Make a reservation that ends when the resource closes
        Reservation.objects.create(resource=r1a, begin=begin,
                                   end=end)

        # Attempt reservation that ends after the resource closes
        with self.assertRaises(ValidationError):
            Reservation.objects.create(resource=r1a, begin=begin,
                                       end=end + datetime.timedelta(hours=1))
