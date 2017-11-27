import pytest
from resources.models import Reservation
from resources.tests.conftest import *


list_url = '/reports/reservation_details/'


@pytest.fixture
def reservation(resource_in_unit, user):
    return Reservation.objects.create(
        resource=resource_in_unit,
        begin='2015-04-04T09:00:00+02:00',
        end='2015-04-04T10:00:00+02:00',
        user=user,
        reserver_name='John Smith',
        event_subject="John's welcome party",
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
    )


def check_valid_response(response):
    headers = response._headers
    assert headers['content-type'][1] == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    assert headers['content-disposition'][1].endswith('.docx')
    assert len(response.content) > 0


@pytest.mark.django_db
def test_get_reservation_details_report(api_client, reservation):
    response = api_client.get(list_url + '?reservation=%s' % reservation.id)
    assert response.status_code == 200

    check_valid_response(response)


@pytest.mark.django_db
def test_daily_reservations_filter_errors(api_client, test_unit, reservation, resource_in_unit):
    response = api_client.get(list_url + '?reservation=592843752987', HTTP_ACCEPT_LANGUAGE='en')
    assert response.status_code == 404
    assert 'does not exist' in str(response.data)

    response = api_client.get(list_url + '?start=abc', HTTP_ACCEPT_LANGUAGE='en')
    assert response.status_code == 400
    assert 'must be a timestamp in ISO' in str(response.data)
