import datetime
import pytest

import arrow
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from resources.models import *


class ReservationTestCase(TestCase):

    def setUp(self):
        u1 = Unit.objects.create(name='Unit 1', id='unit_1', time_zone='Europe/Helsinki')
        u2 = Unit.objects.create(name='Unit 2', id='unit_2', time_zone='Europe/Helsinki')
        rt = ResourceType.objects.create(name='Type 1', id='type_1', main_type='space')
        Resource.objects.create(name='Resource 1a', id='r1a', unit=u1, type=rt)
        Resource.objects.create(name='Resource 1b', id='r1b', unit=u1, type=rt)
        Resource.objects.create(name='Resource 2a', id='r2a', unit=u2, type=rt)
        Resource.objects.create(name='Resource 2b', id='r2b', unit=u2, type=rt)

        p1 = Period.objects.create(start='2116-06-01', end='2116-09-01', unit=u1, name='')
        p2 = Period.objects.create(start='2116-06-01', end='2116-09-01', unit=u2, name='')
        p3 = Period.objects.create(start='2116-06-01', end='2116-09-01', resource_id='r1a', name='')
        Day.objects.create(period=p1, weekday=0, opens='08:00', closes='22:00')
        Day.objects.create(period=p2, weekday=1, opens='08:00', closes='16:00')
        Day.objects.create(period=p3, weekday=0, opens='08:00', closes='18:00')

        u1.update_opening_hours()
        u2.update_opening_hours()

    def test_opening_hours(self):
        r1a = Resource.objects.get(id='r1a')
        r1b = Resource.objects.get(id='r1b')

        date = arrow.get('2116-06-01').date()
        end = arrow.get('2116-06-02').date()
        days = r1a.get_opening_hours(begin=date, end=end)  # Monday
        hours = days[date][0]  # first day object of chosen days
        self.assertEqual(hours['opens'].time(), datetime.time(8, 00))
        self.assertEqual(hours['closes'].time(), datetime.time(18, 00))

        days = r1b.get_opening_hours(begin=date, end=end)  # Monday
        hours = days[date][0]  # first day object of chosen days
        self.assertEqual(hours['opens'].time(), datetime.time(8, 00))
        self.assertEqual(hours['closes'].time(), datetime.time(22, 00))

    def test_reservation(self):
        r1a = Resource.objects.get(id='r1a')
        r1b = Resource.objects.get(id='r1b')

        tz = timezone.get_current_timezone()
        begin = tz.localize(datetime.datetime(2116, 6, 1, 8, 0, 0))
        end = begin + datetime.timedelta(hours=2)

        reservation = Reservation.objects.create(resource=r1a, begin=begin, end=end)
        reservation.clean()

        # Attempt overlapping reservation
        with self.assertRaises(ValidationError):
            reservation = Reservation(resource=r1a, begin=begin, end=end)
            reservation.clean()

        valid_begin = begin + datetime.timedelta(hours=3)
        valid_end = end + datetime.timedelta(hours=3)

        # Attempt incorrectly aligned begin time
        with self.assertRaises(ValidationError):
            reservation = Reservation(resource=r1a, begin=valid_begin + datetime.timedelta(minutes=1), end=valid_end)
            reservation.clean()

        # Attempt incorrectly aligned end time
        with self.assertRaises(ValidationError):
            reservation = Reservation(resource=r1a, begin=valid_begin, end=valid_end + datetime.timedelta(minutes=1))
            reservation.clean()

        # Attempt reservation that starts before the resource opens
        # Should not raise an exception as this check isn't included in model clean
        reservation = Reservation(
            resource=r1a,
            begin=begin - datetime.timedelta(hours=1),
            end=begin
        )
        reservation.clean()

        begin = tz.localize(datetime.datetime(2116, 6, 1, 16, 0, 0))
        end = begin + datetime.timedelta(hours=2)

        # Make a reservation that ends when the resource closes
        reservation = Reservation(resource=r1a, begin=begin, end=end)
        reservation.clean()

        # Attempt reservation that ends after the resource closes
        # Should not raise an exception as this check isn't included in model clean
        reservation = Reservation(resource=r1a, begin=begin, end=end + datetime.timedelta(hours=1))
        reservation.clean()


@pytest.mark.django_db
def test_need_manual_confirmation_metadata_set(resource_in_unit):
    data_set = ReservationMetadataSet.objects.get(name='default')
    assert data_set.supported_fields.exists()
    assert data_set.required_fields.exists()
