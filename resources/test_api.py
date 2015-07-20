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

        #p1 = Period.objects.create(start='2015-06-01', end='2015-09-01', unit=u1, name='')
        p2 = Period.objects.create(start='2015-06-01', end='2015-09-01', unit=u2, name='')
        #p3 = Period.objects.create(start='2015-06-01', end='2015-09-01', resource_id='r1a', name='')
        #Day.objects.create(period=p1, weekday=0, opens='08:00', closes='22:00')
        Day.objects.create(period=p2, weekday=1, opens='08:00', closes='16:00')
        #Day.objects.create(period=p3, weekday=0, opens='08:00', closes='18:00')

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
        tz = timezone.get_current_timezone()
        start = tz.localize(arrow.now().floor("day").naive)
        end = start + datetime.timedelta(days=1)
        format = '%Y-%m-%dT%H:%M:%S%z'
        print("debug", start.isoformat(), end.isoformat())

        # Set opening hours for today (required to make a reservation)
        today = Period.objects.create(start=start.date(), end=end.date(), resource_id='r1a', name='this')
        Day.objects.create(period=today, weekday=start.weekday(), opens='08:00', closes='22:00')

        print("debug", [j for j in Resource.objects.get(id='r1a').reservations.all()])
        # Check that available *and* opening hours are reported correctly for a free resource
        response = self.client.get('/v1/resource/r1a/')
        print("res starting state", response.content)

        # eest_start = start.to(tz="Europe/Helsinki")
        # eest_end = end.to(tz="Europe/Helsinki")
        self.assertContains(response, '"starts":"' + start.isoformat() + '"')
        self.assertContains(response, '"ends":"' + end.isoformat() + '"')
        # self.assertContains(response, '08:00')
        # self.assertContains(response, '22:00')

        # Make a reservation through the API
        res_start = start + datetime.timedelta(hours=8)
        res_end = res_start + datetime.timedelta(hours=2)
        # res_start = '2015-06-01T08:00:00'
        # res_end = '2015-06-01T10:00:00'
        print("start reservation at ", res_start)
        print("end reservation at ", res_end)
        response = self.client.post('/v1/reservation/',
                                    {'resource': 'r1a',
                                     'begin': res_start,
                                     'end': res_end})
        print("reservation", response.content)
        self.assertContains(response, '"resource":"r1a"', status_code=201)

        # Check that available hours are reported correctly for a reserved resource
        response = self.client.get('/v1/resource/r1a/')
        print("res after reservation", response.content)
        print("res debug", res_start, res_end)
        self.assertContains(response, '"starts":"' + start.isoformat())
        self.assertContains(response, '"ends":"' + res_start.isoformat())
        self.assertContains(response, '"starts":"' + res_end.isoformat())
        self.assertContains(response, '"ends":"' + end.isoformat())


class AvailableAPITestCase(APITestCase):

    client = APIClient()

    def setUp(self):
        u1 = Unit.objects.create(name='Unit 1', id='unit_1', time_zone='Europe/Helsinki')
        u2 = Unit.objects.create(name='Unit 2', id='unit_2', time_zone='Europe/Helsinki')
        rt = ResourceType.objects.create(name='Type 1', id='type_1', main_type='space')
        r1a = Resource.objects.create(name='Resource 1a', id='r1a', unit=u1, type=rt)
        r1b = Resource.objects.create(name='Resource 1b', id='r1b', unit=u1, type=rt)
        r2a = Resource.objects.create(name='Resource 2a', id='r2a', unit=u2, type=rt)
        r2b = Resource.objects.create(name='Resource 2b', id='r2b', unit=u2, type=rt)

        fun = Purpose.objects.create(name='Having fun', id='having_fun', main_type='games')
        r1a.purposes.add(fun)
        r2a.purposes.add(fun)

    def test_filters(self):
        # Check that correct resources are returned
        response = self.client.get('/v1/available/?purpose=having_fun')
        print("availability response ", response.content)
        self.assertContains(response, '/r1a')
        self.assertContains(response, '/r2a')
        self.assertNotContains(response, '/r1b')
        self.assertNotContains(response, '/r2b')

        response = self.client.get('/v1/resource/?purpose=having_fun')
        print("resource response ", response.content)
        self.assertContains(response, 'r1a')
        self.assertContains(response, 'r2a')
        self.assertNotContains(response, 'r1b')
        self.assertNotContains(response, 'r2b')

        tz = timezone.get_current_timezone()
        start = tz.localize(arrow.now().floor("day").naive)
        end = start + datetime.timedelta(days=1)

        # Set opening hours for today (required to make a reservation)
        today = Period.objects.create(start=start.date(), end=end.date(), resource_id='r1a', name='')
        Day.objects.create(period=today, weekday=start.weekday(), opens='08:00', closes='22:00')

        # Check that the resource is available for all-day fun-having
        response = self.client.get('/v1/available/?purpose=having_fun&duration=840&start=08:00&end=22:00')
        print("availability response ", response.content)
        self.assertContains(response, '/r1a')

        # Check that the duration cannot be longer than the datetimes specified
        response = self.client.get('/v1/available/?purpose=having_fun&duration=850&start=08:00&end=22:00')
        print("availability response ", response.content)
        self.assertNotContains(response, '/r1a')

        # Make a reservation through the API
        res_start = start + datetime.timedelta(hours=8)
        res_end = res_start + datetime.timedelta(hours=2)
        # res_start = '2015-06-01T08:00:00'
        # res_end = '2015-06-01T10:00:00'
        response = self.client.post('/v1/reservation/',
                                    {'resource': 'r1a',
                                     'begin': res_start,
                                     'end': res_end})
        print("reservation", response.content)
        self.assertContains(response, '"resource":"r1a"', status_code=201)

        # Check that available hours are reported correctly for a reserved resource
        response = self.client.get('/v1/resource/r1a/?start=08:00&end=22:00')
        print("resource after reservation", response.content)
        print("reservation debug", res_start, res_end)
        self.assertContains(response, '"starts":"' + res_end.isoformat())
        self.assertContains(response, '"ends":"' + (res_end + datetime.timedelta(hours=12)).isoformat())

        # Check that all-day fun is no longer to be had
        response = self.client.get('/v1/available/?purpose=having_fun&duration=840&start=08:00&end=22:00')
        print("availability response ", response.content)
        self.assertNotContains(response, '/r1a')

        # Check that our intrepid tester can still have fun for a more limited amount of time
        response = self.client.get('/v1/available/?purpose=having_fun&duration=720&start=08:00&end=22:00')
        print("availability response ", response.content)
        self.assertContains(response, '/r1a')

