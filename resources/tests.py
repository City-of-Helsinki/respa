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
        hours = r1a.get_opening_hours(begin=date)  # Monday
        self.assertEqual(hours['opens'], datetime.time(8, 00))
        self.assertEqual(hours['closes'], datetime.time(18, 00))

        hours = r1b.get_opening_hours(begin=date)  # Monday
        self.assertEqual(hours['opens'], datetime.time(8, 00))
        self.assertEqual(hours['closes'], datetime.time(22, 00))

    def test_reservation(self):
        r1a = Resource.objects.get(id='r1a')
        r1b = Resource.objects.get(id='r1b')

        tz = pytz.timezone('Europe/Helsinki')

        begin = tz.localize(arrow.get('2015-06-01T08:00:00').naive)
        end = begin + datetime.timedelta(hours=2)

        Reservation.objects.create(resource=r1a, begin=begin, end=end)

        # Attempt overlapping reservation
        with self.assertRaises(ValidationError):
            Reservation.objects.create(resource=r1a, begin=begin,
                                       end=end)

        # Attempt reservation that starts before the resource opens
        with self.assertRaises(ValidationError):
            Reservation.objects.create(resource=r1a,
                                       begin=begin - datetime.timedelta(hours=1),
                                       end=end)

        begin = tz.localize(arrow.get('2015-06-01T16:00:00').naive)
        end = begin + datetime.timedelta(hours=2)
        # Make a reservation that ends when the resource closes
        Reservation.objects.create(resource=r1a, begin=begin,
                                   end=end)

        # Attempt reservation that ends after the resource closes
        with self.assertRaises(ValidationError):
            Reservation.objects.create(resource=r1a, begin=begin,
                                       end=end + datetime.timedelta(hours=1))

    def test_api(self):
        response = self.client.get('/v1/unit/')
        self.assertContains(response, 'Unit 1')
        self.assertContains(response, 'Unit 2')

        response = self.client.get('/v1/resource/')
        self.assertContains(response, 'Resource 1a')
        self.assertContains(response, 'Resource 1b')
        self.assertContains(response, 'Resource 2a')
        self.assertContains(response, 'Resource 2b')

        tz = pytz.timezone('Europe/Helsinki')
        start = tz.localize(arrow.get(arrow.now().date()).naive)
        end = start + datetime.timedelta(days=1)
        format = '%Y-%m-%dT%H:%M:%S+03:00'

        # Check that available hours are reported correctly for a free resource
        response = self.client.get('/v1/resource/r1a/')
        print(response.content)
        self.assertContains(response, '"starts":"' + start.strftime(format) + '"')
        self.assertContains(response, '"ends":"' + end.strftime(format) + '"')

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
                                     'begin': res_start,
                                     'end': res_end})
        print(response.content)
        self.assertContains(response, '"resource":"r1a"', status_code=201)

        # Check that available hours are reported correctly for a reserved resource
        response = self.client.get('/v1/resource/r1a/')
        print(response.content)
        self.assertContains(response, '"starts":"' + start.strftime(format))
        self.assertContains(response, '"ends":"' + res_start.strftime(format))
        self.assertContains(response, '"starts":"' + res_end.strftime(format))
        self.assertContains(response, '"ends":"' + end.strftime(format))
