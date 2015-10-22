from datetime import datetime

import arrow
import pytest
from django.conf import settings

from resources.models import Day, Period, Reservation, Resource, ResourceType, Unit

TEST_PERFORMANCE = bool(getattr(settings, "TEST_PERFORMANCE", False))


@pytest.mark.skipif(not TEST_PERFORMANCE, reason="TEST_PERFORMANCE not enabled")
@pytest.mark.django_db
def test_api_resource_scalability(api_client):
    u1 = Unit.objects.create(name='Unit 1', id='unit_1', time_zone='Europe/Helsinki')
    rt = ResourceType.objects.create(name='Type 1', id='type_1', main_type='space')
    p1 = Period.objects.create(start='2015-06-01', end='2015-09-01', unit=u1, name='')
    Day.objects.create(period=p1, weekday=0, opens='08:00', closes='22:00')
    Day.objects.create(period=p1, weekday=1, opens='08:00', closes='16:00')
    # make reservations for the whole day
    begin_res = arrow.get('2015-06-01T08:00:00Z').datetime
    end_res = arrow.get('2015-06-01T16:00:00Z').datetime

    perf_res_list = open('perf_res_list.csv', 'w')
    perf_res_avail = open('perf_res_avail.csv', 'w')
    perf_reservation = open('perf_reservation.csv', 'w')
    perf_res_list.write('Resource listing\n')
    perf_res_list.write('resources, time (s)\n')
    perf_res_avail.write('Availability listing\n')
    perf_res_avail.write('resources, time (s)\n')
    perf_reservation.write('Single resource availability\n')
    perf_reservation.write('Total reservations, time (s)\n')
    for n in [1, 10, 100, 1000]:
        Resource.objects.all().delete()
        for i in range(n):
            resource = Resource.objects.create(name=('Resource ' + str(i)), id=('r' + str(i)), unit=u1, type=rt)
            Reservation.objects.create(resource=resource, begin=begin_res, end=end_res)

        # Time the resource listing (resource query and serialization ~ O(n))
        start = datetime.now()
        response = api_client.get('/v1/resource/')
        end = datetime.now()
        perf_res_list.write(str(n) + ', ' + str(end - start) + '\n')

        # Time the availability listing (resource and reservation queries, serialization and filtering ~ O(n)+O(n))
        start = datetime.now()
        response = api_client.get('/v1/resource/?start=2015-06-01T08:00:00Z&end=2015-06-01T16:00:00Z&duration=5000')
        end = datetime.now()
        perf_res_avail.write(str(n) + ', ' + str(end - start) + '\n')

        # Time single resource availability (resource and reservation queries and serialization ~ O(1))
        start = datetime.now()
        response = api_client.get('/v1/resource/r0?start=2015-06-01T08:00:00Z&end=2015-06-01T16:00:00Z&duration=5000')
        end = datetime.now()
        perf_reservation.write(str(n) + ', ' + str(end - start) + '\n')


@pytest.mark.skipif(not TEST_PERFORMANCE, reason="TEST_PERFORMANCE not enabled")
@pytest.mark.django_db
def test_avail_resource_scalability(client):
    u1 = Unit.objects.create(name='Unit 1', id='unit_1', time_zone='Europe/Helsinki')
    rt = ResourceType.objects.create(name='Type 1', id='type_1', main_type='space')
    p1 = Period.objects.create(start='2015-06-01', end='2015-09-01', unit=u1, name='')
    Day.objects.create(period=p1, weekday=0, opens='08:00', closes='22:00')
    Day.objects.create(period=p1, weekday=1, opens='08:00', closes='16:00')
    # make reservations for the whole day
    begin_res = arrow.get('2015-06-01T08:00:00Z').datetime
    end_res = arrow.get('2015-06-01T16:00:00Z').datetime

    perf_res_list = open('perf_res_list.csv', 'w')
    perf_res_avail = open('perf_res_avail.csv', 'w')
    perf_reservation = open('perf_reservation.csv', 'w')
    perf_res_list.write('Resource listing\n')
    perf_res_list.write('resources, time (s)\n')
    perf_res_avail.write('Availability listing\n')
    perf_res_avail.write('resources, time (s)\n')
    perf_reservation.write('Single resource availability\n')
    perf_reservation.write('Total reservations, time (s)\n')
    for n in [1, 10, 100, 1000]:
        Resource.objects.all().delete()
        for i in range(n):
            resource = Resource.objects.create(name=('Resource ' + str(i)), id=('r' + str(i)), unit=u1, type=rt)
            Reservation.objects.create(resource=resource, begin=begin_res, end=end_res)

        # Time the general availability for n resources and reservations
        start = datetime.now()
        response = client.get('/test/availability?start_date=2015-06-01&end_date=2015-06-30')
        end = datetime.now()
        perf_res_list.write(str(n) + ', ' + str(end - start) + '\n')
