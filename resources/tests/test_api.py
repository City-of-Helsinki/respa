import datetime
import string
import random
import jwt
import pytest

import arrow
from django.utils import timezone
from django.conf import settings
from rest_framework.test import APIClient, APITestCase
from rest_framework_jwt.settings import api_settings

from resources.models import *


def generate_random_string(length):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for x in range(length))


class JWTMixin(object):
    jwt_token = {
        "username": "testuser",
        "email": "test@example.com",
        "first_name": "Test",
        "last_name": "User",
        "department_name": "bestdep",
        "display_name": "Test User",
        "iss": "https://test.example.com/sso",
        "sub": "7af6c103-62aa-47d4-89e2-4bdd45c6ab7b",  # random UUID
        "aud": "TH11btLwVBZyTCVDMshRaWMIqctoNIyy3xQBvKDD",
        "exp": 1446421460
    }

    def authenticated_post(self, url, data, **extra):
        secret_key = generate_random_string(100)
        api_settings.JWT_SECRET_KEY = secret_key
        audience = generate_random_string(40)
        api_settings.JWT_AUDIENCE = audience

        jwt_token = self.jwt_token.copy()
        if 'aud' in extra:
            jwt_token['aud'] = extra['aud']
        else:
            jwt_token['aud'] = api_settings.JWT_AUDIENCE
        if 'exp' in extra:
            jwt_token['exp'] = extra['exp']
        else:
            jwt_token['exp'] = datetime.datetime.utcnow() + datetime.timedelta(hours=1)

        if 'secret_key' in extra:
            secret_key = extra['secret_key']

        encoded_token = jwt.encode(jwt_token, secret_key, algorithm='HS256')
        auth = 'JWT %s' % encoded_token.decode('utf8')
        response = self.client.post(url, data, HTTP_AUTHORIZATION=auth, **extra)
        return response


class ReservationApiTestCase(APITestCase, JWTMixin):
    client = APIClient()

    def setUp(self):
        u1 = Unit.objects.create(name='Unit 1', id='unit_1', time_zone='Europe/Helsinki')
        u2 = Unit.objects.create(name='Unit 2', id='unit_2', time_zone='Europe/Helsinki')
        rt = ResourceType.objects.create(name='Type 1', id='type_1', main_type='space')
        Resource.objects.create(name='Resource 1a', id='r1a', unit=u1, type=rt, reservable=True)
        Resource.objects.create(name='Resource 1b', id='r1b', unit=u1, type=rt, reservable=True)
        Resource.objects.create(name='Resource 2a', id='r2a', unit=u2, type=rt, reservable=True)
        Resource.objects.create(name='Resource 2b', id='r2b', unit=u2, type=rt, reservable=True)

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
        start = tz.localize(arrow.now().floor("day").naive) + datetime.timedelta(days=1)
        end = start + datetime.timedelta(days=1)

        # Set opening hours for tomorrow (required to make a reservation)
        tomorrow = Period.objects.create(start=start.date(), end=end.date(), resource_id='r1a', name='this')
        Day.objects.create(period=tomorrow, weekday=start.weekday(), opens='08:00', closes='22:00')
        Resource.objects.get(id='r1a').update_opening_hours()

        # Check that available *and* opening hours are reported correctly for a free resource
        url = '/v1/resource/r1a/?start=' + start.isoformat().replace('+', '%2b') + '&end=' + end.isoformat().replace('+', '%2b') + '&during_closing=true'
        response = self.client.get(url)

        # eest_start = start.to(tz="Europe/Helsinki")
        # eest_end = end.to(tz="Europe/Helsinki")
        #self.assertContains(response, '"starts":"' + start.isoformat() + '"')
        #self.assertContains(response, '"ends":"' + end.isoformat() + '"')

        # Make a reservation through the API
        res_start = start + datetime.timedelta(hours=8)
        res_end = res_start + datetime.timedelta(hours=2)

        data = {'resource': 'r1a', 'begin': res_start, 'end': res_end}
        response = self.authenticated_post('/v1/reservation/', data)
        self.assertContains(response, '"resource":"r1a"', status_code=201)

        # Check that available hours are reported correctly for a reserved resource
        url = '/v1/resource/r1a/?start=' + start.isoformat().replace('+', '%2b') + '&end=' + end.isoformat().replace('+', '%2b') + '&during_closing=true'
        response = self.client.get(url)
        #self.assertContains(response, '"starts":"' + start.isoformat())
        #self.assertContains(response, '"ends":"' + res_start.isoformat())
        #self.assertContains(response, '"starts":"' + res_end.isoformat())
        #self.assertContains(response, '"ends":"' + end.isoformat())

    def test_jwt_expired(self):
        exp = datetime.datetime.utcnow() - datetime.timedelta(minutes=15)
        response = self.authenticated_post('/v1/reservation/', {}, exp=exp)
        self.assertEqual(response.status_code, 401)

    def test_jwt_invalid_audience(self):
        response = self.authenticated_post('/v1/reservation/', {},
                                           aud=generate_random_string(40))
        self.assertEqual(response.status_code, 401)

    def test_jwt_invalid_secret_key(self):
        response = self.authenticated_post('/v1/reservation/', {},
                                           secret_key=generate_random_string(100))
        self.assertEqual(response.status_code, 401)


@pytest.mark.skip(reason="availability disabled for now")
class AvailableAPITestCase(APITestCase, JWTMixin):

    client = APIClient()

    def setUp(self):
        u1 = Unit.objects.create(name='Unit 1', id='unit_1', time_zone='Europe/Helsinki')
        u2 = Unit.objects.create(name='Unit 2', id='unit_2', time_zone='Europe/Helsinki')
        rt = ResourceType.objects.create(name='Type 1', id='type_1', main_type='space')
        r1a = Resource.objects.create(name='Resource 1a', id='r1a', unit=u1, type=rt, reservable=True)
        r1b = Resource.objects.create(name='Resource 1b', id='r1b', unit=u1, type=rt, reservable=True)
        r2a = Resource.objects.create(name='Resource 2a', id='r2a', unit=u2, type=rt, reservable=True)
        r2b = Resource.objects.create(name='Resource 2b', id='r2b', unit=u2, type=rt, reservable=True)

        fun = Purpose.objects.create(name='Having fun', id='having_fun', parent=None)
        r1a.purposes.add(fun)
        r2a.purposes.add(fun)

    def test_filters(self):
        # Check that correct resources are returned
        response = self.client.get('/v1/resource/?purpose=having_fun')
        print("resource response ", response.content)
        self.assertContains(response, 'r1a')
        self.assertContains(response, 'r2a')
        self.assertNotContains(response, 'r1b')
        self.assertNotContains(response, 'r2b')

        tz = timezone.get_current_timezone()
        start = tz.localize(arrow.now().floor("day").naive) + datetime.timedelta(days=1)
        end = start + datetime.timedelta(days=1)

        # Set opening hours for tomorrow (required to make a reservation)
        tomorrow = Period.objects.create(start=start.date(), end=end.date(), resource_id='r1a', name='')
        Day.objects.create(period=tomorrow, weekday=start.weekday(), opens='08:00', closes='22:00')

        # Check that the resource is available for all-day fun-having
        url = '/v1/resource/?purpose=having_fun&duration=1440&start=' + start.isoformat().replace('+', '%2b') + '&end=' + end.isoformat().replace('+', '%2b') + '&during_closing=true'
        response = self.client.get(url)
        self.assertContains(response, 'r1a')

        # Check that the duration cannot be longer than the datetimes specified
        url = '/v1/resource/?purpose=having_fun&duration=1450&start=' + start.isoformat().replace('+', '%2b') + '&end=' + end.isoformat().replace('+', '%2b') + '&during_closing=true'
        response = self.client.get(url)
        self.assertNotContains(response, 'r1a')

        # Make a reservation through the API
        res_start = start + datetime.timedelta(hours=8)
        res_end = res_start + datetime.timedelta(hours=2)

        data = {'resource': 'r1a', 'begin': res_start, 'end': res_end}
        response = self.authenticated_post('/v1/reservation/', data)
        print("reservation", response.content)
        self.assertContains(response, '"resource":"r1a"', status_code=201)

        # Check that available hours are reported correctly for a reserved resource
        url = '/v1/resource/?purpose=having_fun&start=' + start.isoformat().replace('+', '%2b') + '&end=' + end.isoformat().replace('+', '%2b') + '&during_closing=true'
        response = self.client.get(url)
        print("resource after reservation", response.content)
        print("reservation debug", res_start, res_end)
        self.assertContains(response, '"starts":"' + res_end.isoformat())
        self.assertContains(response, '"ends":"' + (res_end + datetime.timedelta(hours=14)).isoformat())

        # Check that all-day fun is no longer to be had
        url = '/v1/resource/?purpose=having_fun&duration=1440&start=' + start.isoformat().replace('+', '%2b') + '&end=' + end.isoformat().replace('+', '%2b') + '&during_closing=true'
        response = self.client.get(url)
        print("availability response ", response.content)
        self.assertNotContains(response, 'r1a')

        # Check that our intrepid tester can still have fun for a more limited amount of time
        url = '/v1/resource/?purpose=having_fun&duration=720&start=' + start.isoformat().replace('+', '%2b') + '&end=' + end.isoformat().replace('+', '%2b') + '&during_closing=true'
        response = self.client.get(url)
        print("availability response ", response.content)
        self.assertContains(response, 'r1a')

        url = '/v1/resource/?unit=unit_1'
        response = self.client.get(url)
        self.assertContains(response, 'r1a')
        self.assertContains(response, 'r1b')
        self.assertNotContains(response, 'r2a')
        self.assertNotContains(response, 'r2b')

        url = '/v1/resource/?unit=unit_2'
        response = self.client.get(url)
        self.assertContains(response, 'r2a')
        self.assertContains(response, 'r2b')
        self.assertNotContains(response, 'r1a')
        self.assertNotContains(response, 'r1b')


        # FIXME: Check filtering for expired reservations ('all=false')
        # and user filtering.
