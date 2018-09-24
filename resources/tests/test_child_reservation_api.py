from datetime import timedelta, datetime

import pytest
import pytz
from django.core import mail
from django.test.utils import override_settings
from django.urls import reverse

from resources.models import Reservation, Period, Day
from notifications.models import NotificationTemplate, NotificationType
from notifications.tests.utils import check_received_mail_exists


list_url = reverse('incubating:reservation-list')


def get_detail_url(reservation):
    return reverse('incubating:reservation-detail', kwargs={'pk': reservation.pk})


def create_test_datetime(hours=0, minutes=0, year=2115, month=4, day=4, timezone='Europe/Helsinki'):
    return pytz.timezone(timezone).localize(datetime(year, month, day, hours, minutes))


@pytest.fixture(autouse=True)
def force_english(settings):
    settings.LANGUAGE_CODE = 'en'


@pytest.fixture(autouse=True)
def day_and_period(resource_in_unit):
    period = Period.objects.create(
        start='2115-04-01',
        end='2115-05-01',
        resource_id=resource_in_unit.id,
        name='test_period'
    )
    Day.objects.create(period=period, weekday=3, opens='08:00', closes='16:00')
    resource_in_unit.update_opening_hours()


@pytest.fixture
def reservation(resource_in_unit, user):
    return Reservation.objects.create(
        resource=resource_in_unit,
        begin=create_test_datetime(10, 0),
        end=create_test_datetime(12, 0),
        user=user,
        event_subject='some fancy event',
        host_name='esko',
        reserver_name='martta',
    )


@pytest.fixture
def reservation_with_child_reservation(reservation, guide_resource):
    Reservation.objects.create(
        resource=guide_resource,
        begin=create_test_datetime(10, 0),
        end=create_test_datetime(11, 0),
        user=reservation.user,
        parent_reservation=reservation,
    )
    return reservation


@pytest.fixture
def reservation_data(resource_in_unit):
    return {
        'resource': resource_in_unit.pk,
        'begin': create_test_datetime(10, 0),
        'end': create_test_datetime(12, 0),
    }


@pytest.fixture
def guide_reservation_data(guide_resource):
    return {
        'resource': guide_resource.pk,
        'begin': create_test_datetime(10, 0),
        'end': create_test_datetime(11, 0),
    }


@pytest.fixture
def child_reservation_cancelled_template():
    return NotificationTemplate.objects.language('en').create(
        type=NotificationType.CHILD_RESERVATION_CANCELLED,
        subject='Child reservation cancelled.',
        html_body='A child reservation has been cancelled. '
                  'Child resource: {{ resource }} '
                  'Parent resource: {{ parent_reservation.resource }}',
    )


@pytest.fixture
def child_reservation_created_separately_template():
    return NotificationTemplate.objects.language('en').create(
        type=NotificationType.CHILD_RESERVATION_CREATED_SEPARATELY,
        subject='Child reservation created separately.',
        html_body='A child reservation has been created separately. '
                  'Child resource: {{ resource }} '
                  'Parent resource: {{ parent_reservation.resource }}',
    )


@pytest.fixture
def child_reservation(reservation_with_child_reservation):
    return reservation_with_child_reservation.child_reservations.first()


@pytest.mark.django_db
def test_child_reservation_ids_in_reservation_list(user_api_client, reservation, child_reservation):
    response = user_api_client.get(list_url)
    assert response.status_code == 200
    results = response.data['results']
    assert len(results) == 1
    assert results[0]['id'] == reservation.id


@pytest.mark.django_db
def test_nested_child_reservation_in_detail_endpoint_data(user_api_client, reservation, child_reservation):
    url = get_detail_url(reservation)

    response = user_api_client.get(url)
    assert response.status_code == 200
    child_reservations_data = response.data['child_reservations']
    assert len(child_reservations_data) == 1
    child_reservation_data = child_reservations_data[0]
    assert child_reservation_data['id'] == child_reservation.id
    assert child_reservation_data['is_own'] is True


@pytest.mark.django_db
def test_nested_child_reservation_other_user(user_api_client, reservation, child_reservation, user2):
    child_reservation.user = user2
    child_reservation.save()
    url = get_detail_url(reservation)

    response = user_api_client.get(url)
    assert response.status_code == 200
    child_reservations_data = response.data['child_reservations']
    assert len(child_reservations_data) == 1
    child_reservation_data = child_reservations_data[0]
    assert child_reservation_data['id'] == child_reservation.id
    assert child_reservation_data['is_own'] is False
    assert 'user' not in child_reservation_data


@pytest.mark.parametrize('state', (Reservation.CANCELLED, Reservation.DENIED))
@pytest.mark.django_db
def test_only_current_child_reservations_shown(user_api_client, reservation, child_reservation, state, user2):
    user_api_client.force_authenticate(user=user2)
    child_reservation.state = state
    child_reservation.save()
    url = get_detail_url(reservation)

    response = user_api_client.get(url)
    assert response.status_code == 200
    child_reservations_data = response.data['child_reservations']
    assert len(child_reservations_data) == 0


@pytest.mark.django_db
def test_parent_reservation_field_not_in_list_data(user_api_client, reservation, child_reservation):
    response = user_api_client.get(list_url)
    assert response.status_code == 200
    reservation_data = response.data['results'][0]
    assert reservation_data['id'] == reservation.id
    assert 'parent_reservation' not in reservation_data
    child_reservation_data = reservation_data['child_reservations'][0]
    assert 'parent_reservation' not in child_reservation_data


@pytest.mark.django_db
def test_parent_reservation_field_is_in_detail_data(user_api_client, reservation, child_reservation):
    response = user_api_client.get(get_detail_url(child_reservation))
    assert response.status_code == 200
    assert response.data['parent_reservation'] == reservation.id


@pytest.mark.django_db
def test_child_reservation_creation(user_api_client, reservation_data, resource_in_unit, guide_resource, guide_reservation_data):
    reservation_data['child_reservations'] = [guide_reservation_data]
    user = user_api_client.user

    response = user_api_client.post(list_url, data=reservation_data, format='json')
    assert response.status_code == 201

    reservation = Reservation.objects.filter(user=user, parent_reservation=None).latest('created_at')
    assert reservation.resource == resource_in_unit
    assert reservation.begin == reservation_data['begin']
    assert reservation.end == reservation_data['end']

    child_reservation = reservation.child_reservations.last()
    assert child_reservation.user == user
    assert child_reservation.resource == guide_resource
    assert child_reservation.begin == guide_reservation_data['begin']
    assert child_reservation.end == guide_reservation_data['end']


@pytest.mark.django_db
def test_child_reservation_validation(user_api_client, reservation_data, resource_in_unit, guide_resource,
                                    guide_reservation_data):
    guide_resource.reservable = False
    guide_resource.save()
    reservation_data['child_reservations'] = [guide_reservation_data]

    response = user_api_client.post(list_url, data=reservation_data, format='json')
    assert response.status_code == 403
    assert Reservation.objects.count() == 0


@pytest.mark.parametrize('times', (
    {'begin': create_test_datetime(9, 0)},
    {'end': create_test_datetime(13, 30)},
))
@pytest.mark.django_db
def test_child_reservation_times(user_api_client, reservation_data, guide_reservation_data, times):
    guide_reservation_data.update(times)
    reservation_data['child_reservations'] = [guide_reservation_data]

    response = user_api_client.post(list_url, data=reservation_data, format='json')
    assert response.status_code == 400
    assert "Begin and end times must be inside the parent's begin and end times." in str(response.data)


@pytest.mark.django_db
def test_child_reservation_begin_time_must_match(user_api_client, reservation_data, guide_resource,
                                                 guide_reservation_data):
    guide_reservation_data['begin'] = create_test_datetime(10, 30)
    reservation_data['child_reservations'] = [guide_reservation_data]

    response = user_api_client.post(list_url, data=reservation_data, format='json')
    assert response.status_code == 400
    assert "Begin time must match the parent's begin time." in str(response.data)


@pytest.mark.django_db
def test_user_cannot_modify_reservation_with_child_reservation(user_api_client, reservation, child_reservation,
                                                               reservation_data):
    url = get_detail_url(reservation)

    response = user_api_client.put(url, data=reservation_data)
    assert response.status_code == 403

    response = user_api_client.delete(url)
    assert response.status_code == 403


@pytest.mark.django_db
def test_user_cannot_modify_or_cancel_child_reservation(user_api_client, child_reservation, guide_reservation_data):
    url = get_detail_url(child_reservation)

    response = user_api_client.put(url, data=guide_reservation_data)
    assert response.status_code == 403
    response = user_api_client.delete(url)
    assert response.status_code == 403


@pytest.mark.django_db
def test_staff_cannot_modify_child_reservation(user_api_client, general_admin, child_reservation,
                                               guide_reservation_data):
    url = get_detail_url(child_reservation)
    user_api_client.force_authenticate(user=general_admin)

    response = user_api_client.put(url, data=guide_reservation_data)
    assert response.status_code == 403


@pytest.mark.django_db
def test_staff_can_cancel_child_reservation(user_api_client, general_admin, child_reservation, reservation_data):
    url = get_detail_url(child_reservation)
    user_api_client.force_authenticate(user=general_admin)

    response = user_api_client.delete(url)
    assert response.status_code == 204


@pytest.mark.django_db
def test_staff_cannot_cancel_child_reservation(user_api_client, general_admin, child_reservation, guide_reservation_data):
    user_api_client.force_authenticate(user=general_admin)
    response = user_api_client.put(get_detail_url(child_reservation), guide_reservation_data)
    assert response.status_code == 403


@pytest.mark.django_db
def test_user_can_modify_reservation_after_child_reservation_cancelled(user_api_client, reservation, child_reservation,
                                                                       reservation_data):
    child_reservation.state = Reservation.CANCELLED
    child_reservation.save()
    url = get_detail_url(reservation)

    response = user_api_client.put(url, data=reservation_data)
    assert response.status_code == 200

    response = user_api_client.delete(url)
    assert response.status_code == 204


@override_settings(RESPA_MAILS_ENABLED=True)
@pytest.mark.django_db
def test_child_reservation_cancelled_mail(child_reservation, general_admin, child_reservation_cancelled_template):
    parent_reservation = child_reservation.parent_reservation
    parent_reservation.refresh_from_db()
    child_reservation.refresh_from_db()

    child_reservation.set_state(Reservation.CANCELLED, general_admin)
    assert len(mail.outbox) == 1
    excepted_body = 'A child reservation has been cancelled. Child resource: {} Parent resource: {}'.format(
        child_reservation.resource.name, parent_reservation.resource.name
    )
    check_received_mail_exists(
        'Child reservation cancelled.', child_reservation.parent_reservation.user.email, html_body=excepted_body
    )


@pytest.mark.django_db
def test_user_cannot_add_child_reservation_later(user_api_client, reservation, guide_reservation_data):
    guide_reservation_data['parent_reservation'] = reservation.id
    response = user_api_client.post(list_url, data=guide_reservation_data)
    assert response.status_code == 403


@pytest.mark.django_db
def test_staff_add_child_reservation_later(user_api_client, general_admin, reservation, guide_reservation_data):
    user_api_client.force_authenticate(user=general_admin)
    guide_reservation_data['parent_reservation'] = reservation.id
    response = user_api_client.post(list_url, data=guide_reservation_data)
    assert response.status_code == 201


@override_settings(RESPA_MAILS_ENABLED=True)
@pytest.mark.django_db
def test_child_reservation_created_separately_mail(user_api_client, general_admin, reservation, guide_reservation_data,
                                                   child_reservation_created_separately_template):
    guide_reservation_data['begin'] = reservation.begin
    guide_reservation_data['end'] = reservation.begin + timedelta(hours=1)
    user_api_client.force_authenticate(user=general_admin)
    guide_reservation_data['parent_reservation'] = reservation.id
    response = user_api_client.post(list_url, data=guide_reservation_data)
    assert response.status_code == 201

    assert len(mail.outbox) == 1
    excepted_body = 'A child reservation has been created separately. Child resource: {} Parent resource: {}'.format(
        reservation.child_reservations.first().resource.name, reservation.resource.name
    )
    check_received_mail_exists(
        'Child reservation created separately.', reservation.user.email, html_body=excepted_body
    )
