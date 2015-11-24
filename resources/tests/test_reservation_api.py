import pytest
from django.utils import dateparse
from django.core.urlresolvers import reverse

from resources.models import Period, Day, Reservation
from .utils import assert_non_field_errors_contain


@pytest.fixture
def list_url():
    return reverse('reservation-list')


@pytest.mark.django_db
@pytest.fixture(autouse=True)
def day_and_period(resource_in_unit):
    period = Period.objects.create(
        start='2005-04-01',
        end='2115-05-01',
        resource_id=resource_in_unit.id,
        name='test_period'
    )
    Day.objects.create(period=period, weekday=3, opens='08:00', closes='16:00')


@pytest.mark.django_db
@pytest.fixture
def reservation_data(resource_in_unit):
    return {
        'resource': resource_in_unit.pk,
        'begin': '2115-04-04T11:00:00+02:00',
        'end': '2115-04-04T12:00:00+02:00'
    }


@pytest.mark.django_db
@pytest.fixture
def reservation(resource_in_unit, user):
    return Reservation.objects.create(
        resource=resource_in_unit,
        begin='2115-04-04T09:00:00+02:00',
        end='2115-04-04T10:00:00+02:00',
        user=user,
    )


@pytest.mark.django_db
def test_reservation_requires_authenticated_user(api_client, list_url, reservation_data):
    """
    Tests that an unauthenticated user cannot create a reservation.
    """
    response = api_client.post(list_url, data=reservation_data)
    assert response.status_code == 401


@pytest.mark.django_db
def test_authenticated_user_can_make_reservation(api_client, list_url, reservation_data, resource_in_unit, user):
    """
    Tests that an authenticated user can create a reservation.
    """
    api_client.force_authenticate(user=user)

    response = api_client.post(list_url, data=reservation_data)
    assert response.status_code == 201
    reservation = Reservation.objects.filter(user=user).latest('created_at')
    assert reservation.resource == resource_in_unit
    assert reservation.begin == dateparse.parse_datetime('2115-04-04T11:00:00+02:00')
    assert reservation.end == dateparse.parse_datetime('2115-04-04T12:00:00+02:00')


@pytest.mark.django_db
def test_reservation_limit_per_user(api_client, list_url, reservation, reservation_data, user):
    """
    Tests that a user cannot exceed her active reservation limit for one resource.
    """
    api_client.force_authenticate(user=user)

    # the user already has one reservation, making another reservation should not be possible as the active reservation
    # limit is one
    response = api_client.post(list_url, data=reservation_data, HTTP_ACCEPT_LANGUAGE='en')

    assert response.status_code == 400
    assert_non_field_errors_contain(response, 'Maximum number of active reservations for this resource exceeded.')


@pytest.mark.django_db
def test_old_reservations_are_excluded(api_client, list_url, resource_in_unit, reservation_data, user):
    """
    Tests that a reservation in the past doesn't count when checking reservation limit.
    """

    # the user already has this reservation which is in the past.
    Reservation.objects.create(
        resource=resource_in_unit,
        begin=dateparse.parse_datetime('2005-04-07T09:00:00+02:00'),
        end=dateparse.parse_datetime('2005-04-07T10:00:00+02:00'),
        user=user,
    )
    api_client.force_authenticate(user=user)

    # making another reservation should be possible because the other reservation is in the past.
    response = api_client.post(list_url, data=reservation_data, HTTP_ACCEPT_LANGUAGE='en')

    assert response.status_code == 201


@pytest.mark.django_db
def test_staff_has_no_reservation_limit(api_client, list_url, reservation, reservation_data, user):
    """
    Tests that the reservation limits for a resource do not apply to staff.
    """
    user.is_staff = True
    user.save()
    api_client.force_authenticate(user=user)

    # the staff member already has one reservation, and should be able to make a second one regardless of the fact that
    # that the limit is one.
    response = api_client.post(list_url, data=reservation_data, HTTP_ACCEPT_LANGUAGE='en')

    assert response.status_code == 201


@pytest.mark.django_db
def test_normal_user_cannot_make_reservation_outside_open_hours(api_client, list_url, reservation_data, user):
    """
    Tests that a normal user cannot make reservations outside open hours.
    """
    api_client.force_authenticate(user=user)

    # valid begin time, end time after closing time
    reservation_data['end'] = '2115-04-04T21:00:00+02:00'
    response = api_client.post(list_url, data=reservation_data, HTTP_ACCEPT_LANGUAGE='en')
    assert response.status_code == 400
    assert_non_field_errors_contain(response, 'You must start and end the reservation during opening hours')

    # begin time before opens, valid end time
    reservation_data['begin'] = '2115-04-04T05:00:00+02:00'
    reservation_data['end'] = '2115-04-04T10:00:00+02:00'
    response = api_client.post(list_url, data=reservation_data, HTTP_ACCEPT_LANGUAGE='en')
    assert response.status_code == 400
    assert_non_field_errors_contain(response, 'You must start and end the reservation during opening hours')


@pytest.mark.django_db
def test_normal_user_cannot_make_reservation_longer_than_max_period(api_client, list_url, reservation_data, user):
    """
    Tests that a normal user cannot make reservations longer than the resource's max period.
    """
    api_client.force_authenticate(user=user)

    # the reservation's length is 3h (11 -> 14) while the maximum is 2h
    reservation_data['end'] = '2115-04-04T14:00:00+02:00'
    response = api_client.post(list_url, data=reservation_data, HTTP_ACCEPT_LANGUAGE='en')
    assert response.status_code == 400
    assert_non_field_errors_contain(response, 'The maximum reservation length is')


@pytest.mark.django_db
def test_staff_user_can_make_reservation_outside_open_hours(api_client, list_url, reservation_data, user):
    """
    Tests that a staff member can make reservations outside opening hours.

    Also tests that the resource's max period doesn't limit staff.
    """
    user.is_staff = True
    user.save()
    api_client.force_authenticate(user=user)

    # begin time before opening time, end time after closing time, longer than max period 2h
    reservation_data['begin'] = '2115-04-04T05:00:00+02:00'
    reservation_data['end'] = '2115-04-04T21:00:00+02:00'
    response = api_client.post(list_url, data=reservation_data, HTTP_ACCEPT_LANGUAGE='en')
    assert response.status_code == 201


@pytest.mark.django_db
def test_comments_are_only_for_staff(api_client, list_url, reservation_data, user):
    api_client.force_authenticate(user=user)
    reservation_data['comments'] = 'test comment'
    response = api_client.post(list_url, data=reservation_data)
    assert response.status_code == 400
    user.is_staff = True
    user.save()
    response = api_client.post(list_url, data=reservation_data)
    assert response.status_code == 201

    response = api_client.get(response.data['url'])
    assert response.data['comments'] == 'test comment'

    user.is_staff = False
    user.save()
    response = api_client.get(response.data['url'])
    assert 'comments' not in response.data


@pytest.mark.django_db
def test_user_data_correct_and_only_for_staff(api_client, reservation, user):
    """
    Tests that user object is returned within Reservation data and it is in the correct form.

    Also tests that only staff can see the user object.
    """
    api_client.force_authenticate(user=user)
    detail_url = reverse('reservation-detail', kwargs={'pk': reservation.pk})
    response = api_client.get(detail_url)
    assert 'user' not in response.data

    user.is_staff = True
    user.save()
    response = api_client.get(detail_url)
    user_obj = response.data['user']
    assert len(user_obj) == 3
    assert user_obj['display_name'] == 'Cem Kaner'
    assert user_obj['email'] == 'cem@kaner.com'
    assert user_obj['id'] is not None
