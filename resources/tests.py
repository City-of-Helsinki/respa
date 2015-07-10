import pytz
import datetime
import arrow
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APITestCase, APIRequestFactory, APIClient
from .models import *


class ReservationTestCase(APITestCase):

    client = APIClient()

    def setUp(self):
        u1 = Unit.objects.create(name='Unit 1', id='unit_1', time_zone='Europe/Helsinki')
        u2 = Unit.objects.create(name='Unit 2', id='unit_2', time_zone='Europe/Helsinki')
        rt = ResourceType.objects.create(name='Type 1', id='type_1', main_type='space')
        Resource.objects.create(name='Resource 1a', id='r1a', unit=u1, type=rt)
        Resource.objects.create(name='Resource 1b', id='r1b', unit=u1, type=rt)
        Resource.objects.create(name='Resource 2a', id='r2a', unit=u2, type=rt)
        Resource.objects.create(name='Resource 2b', id='r2b', unit=u2, type=rt)
        Purpose.objects.create(name='Having fun', id='having_fun', main_type='games')

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

        begin = arrow.get('2015-06-01T08:00:00')
        end = begin + datetime.timedelta(hours=2)

        Reservation.objects.create(resource=r1a, begin=begin.datetime, end=end.datetime)

        # Attempt overlapping reservation
        with self.assertRaises(ValidationError):
            Reservation.objects.create(resource=r1a, begin=begin,
                                       end=end)

        # Attempt reservation that starts before the resource opens
        with self.assertRaises(ValidationError):
            Reservation.objects.create(resource=r1a,
                                       begin=begin - datetime.timedelta(hours=1),
                                       end=end)

        begin = arrow.get('2015-06-01T16:00:00')
        end = begin + datetime.timedelta(hours=2)
        # Make a reservation that ends when the resource closes
        Reservation.objects.create(resource=r1a, begin=begin.datetime,
                                   end=end.datetime)

        # Attempt reservation that ends after the resource closes
        with self.assertRaises(ValidationError):
            Reservation.objects.create(resource=r1a, begin=begin.datetime,
                                       end=end.datetime + datetime.timedelta(hours=1))

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


class ReservationApiTestCase(APITestCase):

    client = APIClient()

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

    
    def test_api(self):
        response = self.client.get('/v1/unit/')
        self.assertContains(response, 'Unit 1')
        self.assertContains(response, 'Unit 2')

        response = self.client.get('/v1/resource/')
        self.assertContains(response, 'Resource 1a')
        self.assertContains(response, 'Resource 1b')
        self.assertContains(response, 'Resource 2a')
        self.assertContains(response, 'Resource 2b')

        # Check that available hours are reported correctly for a free resource

        start = arrow.get().floor("day")
        end = start + datetime.timedelta(days=1)
        format = '%Y-%m-%dT%H:%M:%S%z'
        print("debug", start, end)

        # Check that available hours are reported correctly for a free resource
        response = self.client.get('/v1/resource/r1a/')
        print("res starting state", response.content)

        eest_start = start.to(tz="Europe/Helsinki")
        eest_end = end.to(tz="Europe/Helsinki")
        self.assertContains(response, '"starts":"' + eest_start.isoformat() + '"')
        self.assertContains(response, '"ends":"' + eest_end.isoformat() + '"')

        # Set opening hours for today (required to make a reservation)
        today = Period.objects.create(start=start.date(), end=end.date(), resource_id='r1a', name='')
        Day.objects.create(period=today, weekday=start.weekday(), opens='08:00', closes='22:00')

        # Make a reservation through the API
        res_start = start + datetime.timedelta(hours=8)
        res_end = res_start + datetime.timedelta(hours=2)
        # res_start = '2015-06-01T08:00:00'
        # res_end = '2015-06-01T10:00:00'
        response = self.client.post('/v1/reservation/',
                                    {'resource': 'r1a',
                                     'begin': res_start.to(tz="UTC"),
                                     'end': res_end.to(tz="UTC")})
        print("reservation", response.content)
        self.assertContains(response, '"resource":"r1a"', status_code=201)

        # Check that available hours are reported correctly for a reserved resource
        response = self.client.get('/v1/resource/r1a/')
        print("res after reservation", response.content)
        print("res debug", res_start, res_end)
        self.assertContains(response, '"starts":"' + start.to(tz="Europe/Helsinki").isoformat())
        self.assertContains(response, '"ends":"' + res_start.to(tz="Europe/Helsinki").isoformat())
        self.assertContains(response, '"starts":"' + res_end.to(tz="Europe/Helsinki").isoformat())
        self.assertContains(response, '"ends":"' + end.to(tz="Europe/Helsinki").isoformat())
