import pytest
from freezegun import freeze_time
from django.utils import dateparse
from resources.models import Reservation
from resources.tests.conftest import *


list_url = '/reports/daily_reservations/'


@pytest.fixture
def reservation(resource_in_unit, user):
    return Reservation.objects.create(
        resource=resource_in_unit,
        begin='2015-04-04T09:00:00+02:00',
        end='2015-04-04T10:00:00+02:00',
        user=user,
        reserver_name='John Smith',
        event_subject="John's welcome party",
        state=Reservation.CONFIRMED
    )


@pytest.fixture
def reservation2(resource_in_unit2, user):
    return Reservation.objects.create(
        resource=resource_in_unit2,
        begin='2015-04-04T15:00:00+02:00',
        end='2015-04-04T16:00:00+02:00',
        user=user,
        reserver_name='Mike Smith',
        event_subject="John's farewell party",
        state=Reservation.CONFIRMED
    )


def check_valid_response(response):
    headers = response._headers
    assert headers['content-type'][1] == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    assert headers['content-disposition'][1].endswith('.docx')
    assert len(response.content) > 0


@pytest.mark.django_db
def test_daily_reservations_by_unit_and_day(api_client, test_unit, reservation):
    reservation_datetime = dateparse.parse_datetime(reservation.begin)
    reservation_date_str = '%s-%s-%s' % (
        reservation_datetime.year, reservation_datetime.month, reservation_datetime.day
    )

    response = api_client.get(list_url + '?unit=%s&day=%s' % (test_unit.id, reservation_date_str))
    assert response.status_code == 200

    check_valid_response(response)


@freeze_time('2015-04-04')
@pytest.mark.django_db
def test_daily_reservations_by_resources(api_client, test_unit, reservation, reservation2, resource_in_unit,
                                         resource_in_unit2):
    resource_in_unit2.unit = test_unit
    resource_in_unit2.save(update_fields=('unit',))

    # one resource
    response = api_client.get(list_url + '?resource=%s' % resource_in_unit.id)
    assert response.status_code == 200
    check_valid_response(response)
    first_content_length = len(response.content)

    # two resources
    response = api_client.get(list_url + '?resource=%s,%s' % (resource_in_unit.id, resource_in_unit2.id))
    assert response.status_code == 200
    check_valid_response(response)
    assert len(response.content) > first_content_length


@pytest.mark.django_db
def test_daily_reservations_filter_errors(api_client, test_unit, reservation, resource_in_unit):
    response = api_client.get(list_url + '', HTTP_ACCEPT_LANGUAGE='en')
    assert response.status_code == 400
    assert 'Either unit or a valid resource' in response.data['detail']

    response = api_client.get(list_url + '?day=bogus-day&unit=%s' % test_unit.id)
    assert response.status_code == 400
    assert 'day' in response.data['detail']

    response = api_client.get(list_url + '?unit=bogus-unit')
    assert response.status_code == 404
    assert 'unit' in response.data['detail']
