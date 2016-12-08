import pytest
import datetime
import re
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.core import mail
from django.test.utils import override_settings
from django.utils import dateparse, timezone
from guardian.shortcuts import assign_perm
from freezegun import freeze_time

from resources.models import (Period, Day, Reservation, Resource, ReservationMetadataField, ReservationMetadataSet)
from users.models import User
from .utils import check_disallowed_methods, assert_non_field_errors_contain, check_received_mail_exists


DEFAULT_RESERVATION_EXTRA_FIELDS = ('reserver_name', 'reserver_phone_number', 'reserver_address_street',
                                    'reserver_address_zip', 'reserver_address_city', 'billing_address_street',
                                    'billing_address_zip', 'billing_address_city', 'company', 'event_description',
                                    'reserver_id', 'number_of_participants', 'reserver_email_address')

DEFAULT_REQUIRED_RESERVATION_EXTRA_FIELDS = ('reserver_name', 'reserver_phone_number', 'reserver_address_street',
                                             'reserver_address_zip', 'reserver_address_city', 'event_description',
                                             'reserver_id', 'reserver_email_address')


@pytest.fixture
def list_url():
    return reverse('reservation-list')


@pytest.fixture
def detail_url(reservation):
    return reverse('reservation-detail', kwargs={'pk': reservation.pk})


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


@pytest.fixture
def reservation_data_extra(reservation_data):
    extra_data = reservation_data.copy()
    extra_data.update({
        'reserver_name': 'Test Reserver',
        'reserver_phone_number': '0700555555',
        'reserver_address_street': 'Omenatie 102',
        'reserver_address_zip': '00930',
        'reserver_address_city': 'Helsinki',
        'event_description': 'a very secret meeting',
        'reserver_id': '1234567-8',
        'number_of_participants': 5000,
        'billing_address_street': 'Pihlajakatu',
        'billing_address_zip': '00001',
        'billing_address_city': 'Tampere',
        'company': 'a very secret association',
        'reserver_email_address': 'test.reserver@test.com',
    })
    return extra_data


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
@pytest.fixture
def other_resource(space_resource_type, test_unit):
    return Resource.objects.create(
        type=space_resource_type,
        authentication="none",
        name="other resource",
        unit=test_unit,
        id="otherresourceid",
    )


@pytest.fixture
def reservations_in_all_states(resource_in_unit, user):
    all_states = (Reservation.CANCELLED, Reservation.CONFIRMED, Reservation.DENIED, Reservation.REQUESTED)
    reservations = dict()
    for i, state in enumerate(all_states, 4):
        reservations[state] = Reservation.objects.create(
            resource=resource_in_unit,
            begin='2115-04-0%sT09:00:00+02:00' % i,
            end='2115-04-0%sT10:00:00+02:00' % i,
            user=user,
            state=state
        )
    return reservations


@pytest.mark.django_db
def test_disallowed_methods(all_user_types_api_client, list_url):
    """
    Tests that PUT, PATCH and DELETE aren't allowed to reservation list endpoint.
    """
    check_disallowed_methods(all_user_types_api_client, (list_url, ), ('put', 'patch', 'delete'))


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
def test_authenticated_user_can_modify_reservation(
        api_client, detail_url, reservation_data, resource_in_unit, user):
    """
    Tests that an authenticated user can modify her own reservation
    """
    api_client.force_authenticate(user=user)

    response = api_client.put(detail_url, data=reservation_data)
    assert response.status_code == 200
    reservation = Reservation.objects.get(pk=response.data['id'])
    assert reservation.resource == resource_in_unit
    assert reservation.begin == dateparse.parse_datetime('2115-04-04T11:00:00+02:00')
    assert reservation.end == dateparse.parse_datetime('2115-04-04T12:00:00+02:00')


@pytest.mark.django_db
def test_authenticated_user_can_delete_reservation(api_client, detail_url, reservation, user):
    """
    Tests that an authenticated user can delete her own reservation
    """

    api_client.force_authenticate(user=user)
    reservation_id = reservation.id
    response = api_client.delete(detail_url)
    assert response.status_code == 204
    assert Reservation.objects.filter(pk=reservation_id).count() == 1
    reservation.refresh_from_db()
    assert reservation.state == Reservation.CANCELLED


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

    # invalid day
    reservation_data['begin'] = '2115-06-01T09:00:00+02:00'
    reservation_data['end'] = '2115-06-01T10:00:00+02:00'
    response = api_client.post(list_url, data=reservation_data, HTTP_ACCEPT_LANGUAGE='en')
    assert response.status_code == 400
    assert_non_field_errors_contain(response, 'You must start and end the reservation during opening hours')

    # valid begin time, end time after closing time
    reservation_data['begin'] = '2115-04-04T10:00:00+02:00'
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


@pytest.mark.django_db
def test_reservation_can_be_modified_by_overlapping_reservation(api_client, reservation, reservation_data, user):
    """
    Tests that a reservation can be modified with times that overlap with the original times.
    """
    api_client.force_authenticate(user=user)
    detail_url = reverse('reservation-detail', kwargs={'pk': reservation.pk})

    # try to extend the original reservation by 1 hour
    reservation_data['begin'] = '2115-04-04T09:00:00+02:00'
    reservation_data['end'] = '2115-04-04T11:00:00+02:00'
    response = api_client.put(detail_url, reservation_data)
    assert response.status_code == 200
    reservation = Reservation.objects.get(pk=reservation.pk)
    assert reservation.begin == dateparse.parse_datetime('2115-04-04T09:00:00+02:00')
    assert reservation.end == dateparse.parse_datetime('2115-04-04T11:00:00+02:00')


@pytest.mark.django_db
def test_non_reservable_resource_restrictions(api_client, list_url, resource_in_unit, reservation_data, user):
    """
    Tests that a normal user cannot make a reservation to a non reservable resource but staff can.

    Creating a new reservation with POST and updating an existing one with PUT are both tested.
    """
    resource_in_unit.reservable = False
    resource_in_unit.save()
    api_client.force_authenticate(user=user)
    response = api_client.post(list_url, data=reservation_data)
    assert response.status_code == 403

    # Create a reservation and try to change that with PUT
    reservation = Reservation.objects.create(
        resource=resource_in_unit,
        begin=dateparse.parse_datetime('2115-04-07T09:00:00+02:00'),
        end=dateparse.parse_datetime('2115-04-07T10:00:00+02:00'),
        user=user,
    )
    detail_url = reverse('reservation-detail', kwargs={'pk': reservation.pk})
    response = api_client.put(detail_url, reservation_data)
    assert response.status_code == 403

    # a staff member should be allowed to create and update
    user.is_staff = True
    user.save()
    response = api_client.post(list_url, data=reservation_data)
    assert response.status_code == 201
    reservation_data['begin'] = dateparse.parse_datetime('2115-04-08T09:00:00+02:00')
    reservation_data['end'] = dateparse.parse_datetime('2115-04-08T10:00:00+02:00')
    response = api_client.put(detail_url, data=reservation_data)
    assert response.status_code == 200


@pytest.mark.django_db
def test_reservation_restrictions_by_owner(api_client, list_url, reservation, reservation_data, user, user2):
    """
    Tests that a normal user can't modify other people's reservations while a staff member can.
    """
    detail_url = reverse('reservation-detail', kwargs={'pk': reservation.pk})
    api_client.force_authenticate(user=user2)

    response = api_client.put(detail_url, reservation_data)
    assert response.status_code == 403
    response = api_client.delete(detail_url, reservation_data)
    assert response.status_code == 403

    # a staff member should be allowed to perform every modifying method even that she is not the user in
    # the reservation
    user2.is_staff = True
    user2.save()
    response = api_client.put(detail_url, reservation_data)
    assert response.status_code == 200
    response = api_client.delete(detail_url, reservation_data)
    assert response.status_code == 204


@pytest.mark.django_db
def test_normal_users_cannot_make_reservations_for_others(
        api_client, list_url, reservation, reservation_data, user, user2):
    """
    Tests that a normal user cannot make a reservation for other people.
    """
    api_client.force_authenticate(user=user)
    detail_url = reverse('reservation-detail', kwargs={'pk': reservation.pk})

    # set bigger max reservations limit so that it won't be a limiting factor here
    reservation.resource.max_reservations_per_user = 2
    reservation.resource.save()

    # set another user for new reservations
    reservation_data['user'] = {'id': user2.uuid}

    # modify an existing reservation, and verify that user isn't changed
    response = api_client.put(detail_url, data=reservation_data, format='json')
    assert response.status_code == 200
    new_reservation = Reservation.objects.get(id=response.data['id'])
    assert new_reservation.user == user

    # make a new reservation and verify that user isn't the other one
    reservation_data['begin'] = dateparse.parse_datetime('2115-04-04T13:00:00+02:00')
    reservation_data['end'] = dateparse.parse_datetime('2115-04-04T14:00:00+02:00')
    response = api_client.post(list_url, data=reservation_data, format='json')
    assert response.status_code == 201
    new_reservation = Reservation.objects.get(id=response.data['id'])
    assert new_reservation.user == user


@pytest.mark.django_db
def test_reservation_staff_members_can_make_reservations_for_others(
        api_client, list_url, reservation, reservation_data, user, user2):
    """
    Tests that a staff member can make reservations for other people without normal user restrictions.
    """
    user.is_staff = True
    user.save()
    api_client.force_authenticate(user=user)

    # dealing with another user's reservation
    reservation.user = user2
    reservation.save()
    reservation_data['user'] = {'id': user2.uuid}

    # modify an existing reservation
    detail_url = reverse('reservation-detail', kwargs={'pk': reservation.pk})
    response = api_client.put(detail_url, data=reservation_data, format='json')
    assert response.status_code == 200
    new_reservation = Reservation.objects.get(id=response.data['id'])
    assert new_reservation.user == user2

    # create a new reservation, which is also too long, outside the opening hours and exceeds normal user
    # reservation limit. creating such a reservation for a normal user should be possible for a staff member
    reservation_data['begin'] = dateparse.parse_datetime('2115-04-04T13:00:00+02:00')
    reservation_data['end'] = dateparse.parse_datetime('2115-04-04T20:00:00+02:00')
    response = api_client.post(list_url, data=reservation_data, format='json')
    assert response.status_code == 201
    new_reservation = Reservation.objects.get(id=response.data['id'])
    assert new_reservation.user == user2


@pytest.mark.django_db
def test_reservation_user_filter(api_client, list_url, reservation, resource_in_unit, user, user2):
    """
    Tests that reservation user and is_own filtering work correctly.
    """

    reservation2 = Reservation.objects.create(
        resource=resource_in_unit,
        begin=dateparse.parse_datetime('2115-04-07T11:00:00+02:00'),
        end=dateparse.parse_datetime('2115-04-07T12:00:00+02:00'),
        user=user2,
    )

    # even unauthenticated user should see all the reservations
    response = api_client.get(list_url)
    assert response.data['count'] == 2

    # filtering by user
    response = api_client.get(list_url + '?user=%s' % user.uuid)
    assert response.data['count'] == 1
    assert response.data['results'][0]['id'] == reservation.id

    # filtering by is_own
    api_client.force_authenticate(user=user)
    response = api_client.get(list_url + '?is_own=true')
    assert response.data['count'] == 1
    assert response.data['results'][0]['id'] == reservation.id
    response = api_client.get(list_url + '?is_own=false')
    assert response.data['count'] == 1
    assert response.data['results'][0]['id'] == reservation2.id


@pytest.mark.django_db
def test_reservation_time_filters(api_client, list_url, reservation, resource_in_unit, user):
    reservation2 = Reservation.objects.create(
        resource=resource_in_unit,
        begin=dateparse.parse_datetime('2015-04-07T11:00:00+02:00'),
        end=dateparse.parse_datetime('2015-04-07T12:00:00+02:00'),
        user=user,
    )

    # without the filter, only the reservation in the future should be returned
    response = api_client.get(list_url)
    assert response.data['count'] == 1
    assert response.data['results'][0]['id'] == reservation.id

    # with the 'all' filter, both reservations should be returned
    response = api_client.get(list_url + '?all=true')
    assert response.data['count'] == 2
    assert {reservation.id, reservation2.id}.issubset(set(res['id'] for res in response.data['results']))

    # with start or end, both reservations should be returned
    # filtering by start date only
    response = api_client.get(list_url + '?start=2065-04-06')
    assert response.data['count'] == 1
    assert response.data['results'][0]['id'] == reservation.id

    # filtering by end date only
    response = api_client.get(list_url + '?end=2065-04-06')
    assert response.data['count'] == 1
    assert response.data['results'][0]['id'] == reservation2.id

    # filtering by start and end times
    response = api_client.get(list_url + '?start=2065-04-06T11:00:00%2b02:00' + '&end=2065-04-06T12:00:00%2b02:00')
    assert response.data['count'] == 0
    response = api_client.get(list_url + '?start=2005-04-07T11:30:00%2b02:00' + '&end=2115-04-04T09:30:00%2b02:00')
    assert response.data['count'] == 2
    assert {reservation.id, reservation2.id}.issubset(set(res['id'] for res in response.data['results']))


@pytest.mark.parametrize("input_hours,input_mins,expected", [
    (2, 30, '2 hours 30 minutes'),
    (1, 30, '1 hour 30 minutes'),
    (1, 0, '1 hour'),
    (0, 30, '30 minutes'),
    (0, 1, '1 minute'),
])
@pytest.mark.django_db
def test_max_reservation_period_error_message(
        api_client, list_url, resource_in_unit, reservation_data, user, input_hours, input_mins, expected):
    """
    Tests that maximum reservation period error is returned in correct humanized form.
    """

    reservation_data['end'] = '2115-04-04T16:00:00+02:00'  # too long reservation

    resource_in_unit.max_period=datetime.timedelta(hours=input_hours, minutes=input_mins)
    resource_in_unit.save()

    api_client.force_authenticate(user=user)
    response = api_client.post(list_url, data=reservation_data, HTTP_ACCEPT_LANGUAGE='en')
    assert response.status_code == 400
    assert response.data['non_field_errors'][0] == 'The maximum reservation length is %s' % expected


@pytest.mark.django_db
def test_reservation_excels(staff_api_client, list_url, detail_url, reservation, user):
    """
    Tests that reservation list and detail endpoints return .xlsx files when requested
    """

    response = staff_api_client.get(
        list_url,
        HTTP_ACCEPT='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        HTTP_ACCEPT_LANGUAGE='en',
    )
    assert response.status_code == 200
    assert response._headers['content-disposition'] == ('Content-Disposition', 'attachment; filename=reservations.xlsx')
    assert len(response.content) > 0

    response = staff_api_client.get(
        detail_url,
        HTTP_ACCEPT='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        HTTP_ACCEPT_LANGUAGE='en',
    )
    assert response.status_code == 200
    assert response._headers['content-disposition'] == (
        'Content-Disposition', 'attachment; filename=reservation-{}.xlsx'.format(reservation.pk))
    assert len(response.content) > 0


@pytest.mark.parametrize('need_manual_confirmation, expected_state', [
    (False, Reservation.CONFIRMED),
    (True, Reservation.REQUESTED)
])
@pytest.mark.django_db
def test_state_on_new_reservations(user_api_client, list_url, reservation_data_extra, resource_in_unit,
                                   need_manual_confirmation, expected_state):
    resource_in_unit.need_manual_confirmation = need_manual_confirmation
    if need_manual_confirmation:
        resource_in_unit.reservation_metadata_set = ReservationMetadataSet.objects.get(name='default')
    resource_in_unit.save()
    response = user_api_client.post(list_url, data=reservation_data_extra)
    assert response.status_code == 201
    reservation = Reservation.objects.latest('created_at')
    assert reservation.state == expected_state


@pytest.mark.parametrize('state', [
    'illegal_state',
    '',
    None,
])
@pytest.mark.django_db
def test_illegal_state_set(user_api_client, list_url, detail_url, reservation_data, state):
    reservation_data['state'] = state
    response = user_api_client.post(list_url, data=reservation_data, format='json')
    assert response.status_code == 400
    assert 'state' in response.data
    response = user_api_client.put(detail_url, data=reservation_data, format='json')
    assert response.status_code == 400
    assert 'state' in response.data


@pytest.mark.parametrize('need_manual_confirmation', [
    False,
    True
])
@pytest.mark.django_db
def test_extra_fields_visibility(user_api_client, list_url, detail_url, reservation, resource_in_unit,
                                 need_manual_confirmation):
    resource_in_unit.need_manual_confirmation = need_manual_confirmation
    if need_manual_confirmation:
        resource_in_unit.reservation_metadata_set = ReservationMetadataSet.objects.get(name='default')
    resource_in_unit.save()

    for url in (list_url, detail_url):
        response = user_api_client.get(url)
        assert response.status_code == 200
        reservation_data = response.data['results'][0] if 'results' in response.data else response.data
        for field_name in DEFAULT_RESERVATION_EXTRA_FIELDS:
            assert (field_name in reservation_data) is need_manual_confirmation


@pytest.mark.django_db
def test_extra_fields_required_for_paid_reservations(user_api_client, staff_api_client, staff_user, list_url,
                                                     resource_in_unit, reservation_data):
    resource_in_unit.need_manual_confirmation = True
    resource_in_unit.reservation_metadata_set = ReservationMetadataSet.objects.get(name='default')
    resource_in_unit.save()

    response = user_api_client.post(list_url, data=reservation_data)
    assert response.status_code == 400
    assert set(DEFAULT_REQUIRED_RESERVATION_EXTRA_FIELDS) == set(response.data)

    response = staff_api_client.post(list_url, data=reservation_data)
    assert response.status_code == 400
    assert set(DEFAULT_REQUIRED_RESERVATION_EXTRA_FIELDS) == set(response.data)

    assign_perm('can_approve_reservation', staff_user, resource_in_unit.unit)
    response = staff_api_client.post(list_url, data=reservation_data)
    assert response.status_code == 400
    assert set(DEFAULT_REQUIRED_RESERVATION_EXTRA_FIELDS) == set(response.data)


@pytest.mark.django_db
def test_staff_event_restrictions(user_api_client, staff_api_client, staff_user, list_url, resource_in_unit,
                                  reservation_data):
    resource_in_unit.need_manual_confirmation = True
    resource_in_unit.reservation_metadata_set = ReservationMetadataSet.objects.get(name='default')
    resource_in_unit.save()
    reservation_data['staff_event'] = True

    # normal user
    response = user_api_client.post(list_url, data=reservation_data)
    assert response.status_code == 400
    assert set(DEFAULT_REQUIRED_RESERVATION_EXTRA_FIELDS) == set(response.data)

    # staff member
    response = staff_api_client.post(list_url, data=reservation_data)
    assert response.status_code == 400
    assert set(DEFAULT_REQUIRED_RESERVATION_EXTRA_FIELDS) == set(response.data)

    # staff with permission but reserver_name and event_description missing
    assign_perm('can_approve_reservation', staff_user, resource_in_unit.unit)
    response = staff_api_client.post(list_url, data=reservation_data)
    assert response.status_code == 400
    assert {'reserver_name', 'event_description'} == set(response.data)


@pytest.mark.django_db
def test_new_staff_event_gets_confirmed(user_api_client, staff_api_client, staff_user, list_url, resource_in_unit,
                                      reservation_data, reservation_data_extra):
    resource_in_unit.need_manual_confirmation = True
    resource_in_unit.reservation_metadata_set = ReservationMetadataSet.objects.get(name='default')
    resource_in_unit.save()
    reservation_data['staff_event'] = True

    # reservation should not be be confirmed if the user doesn't have approve permission
    response = staff_api_client.post(list_url, data=reservation_data_extra)
    assert response.status_code == 201
    reservation = Reservation.objects.get(id=response.data['id'])
    assert reservation.state == Reservation.REQUESTED

    reservation.delete()

    assign_perm('can_approve_reservation', staff_user, resource_in_unit.unit)
    reservation_data['reserver_name'] = 'herra huu'
    reservation_data['event_description'] = 'herra huun bileet'
    response = staff_api_client.post(list_url, data=reservation_data)
    assert response.status_code == 201
    reservation = Reservation.objects.get(id=response.data['id'])
    assert reservation.state == Reservation.CONFIRMED


@pytest.mark.django_db
def test_extra_fields_can_be_set_for_paid_reservations(user_api_client, list_url, reservation_data_extra,
                                                      resource_in_unit):
    resource_in_unit.max_reservations_per_user = 2
    resource_in_unit.need_manual_confirmation = True
    resource_in_unit.reservation_metadata_set = ReservationMetadataSet.objects.get(name='default')
    resource_in_unit.save()

    response = user_api_client.post(list_url, data=reservation_data_extra)
    assert response.status_code == 201
    reservation = Reservation.objects.latest('created_at')
    assert reservation.reserver_address_street == 'Omenatie 102'

    reservation_data_extra['reserver_address_street'] = 'Karhutie 8'
    response = user_api_client.put('%s%s/' % (list_url, reservation.pk), data=reservation_data_extra)
    assert response.status_code == 200
    reservation.refresh_from_db()
    assert reservation.reserver_address_street == 'Karhutie 8'


@pytest.mark.django_db
def test_extra_fields_ignored_for_non_paid_reservations(user_api_client, list_url, reservation_data_extra,
                                                        resource_in_unit):
    response = user_api_client.post(list_url, data=reservation_data_extra)
    assert response.status_code == 201
    reservation = Reservation.objects.latest('created_at')
    assert reservation.reserver_name == ''
    assert reservation.number_of_participants is None


@pytest.mark.django_db
def test_user_can_see_her_reservations_in_all_states(user_api_client, list_url, reservations_in_all_states):
    response = user_api_client.get(list_url)
    assert response.status_code == 200
    assert response.data['count'] == 4


@pytest.mark.django_db
def test_user_cannot_see_others_denied_or_cancelled_reservations(api_client, user2, list_url,
                                                                 reservations_in_all_states):
    api_client.force_authenticate(user=user2)
    response = api_client.get(list_url)
    assert response.status_code == 200
    assert response.data['count'] == 2
    assert set([Reservation.CONFIRMED, Reservation.REQUESTED]) == set(r['state'] for r in response.data['results'])


@pytest.mark.django_db
def test_staff_can_see_reservations_in_all_states(staff_api_client, list_url, reservations_in_all_states):
    response = staff_api_client.get(list_url)
    assert response.status_code == 200
    assert response.data['count'] == 4


@pytest.mark.django_db
def test_reservation_cannot_be_confirmed_without_permission(user_api_client, staff_api_client, detail_url, reservation,
                                                            reservation_data):
    reservation.state = Reservation.REQUESTED
    reservation.save()
    reservation_data['state'] = Reservation.CONFIRMED

    response = user_api_client.put(detail_url, data=reservation_data)
    assert response.status_code == 400
    assert 'state' in response.data

    response = staff_api_client.put(detail_url, data=reservation_data)
    assert response.status_code == 400
    assert 'state' in response.data


@pytest.mark.django_db
def test_reservation_can_be_confirmed_with_permission(staff_api_client, staff_user, detail_url, reservation,
                                                      reservation_data):
    reservation.state = Reservation.REQUESTED
    reservation.save()
    reservation_data['state'] = Reservation.CONFIRMED
    assign_perm('can_approve_reservation', staff_user, reservation.resource.unit)

    response = staff_api_client.put(detail_url, data=reservation_data)
    assert response.status_code == 200
    reservation.refresh_from_db()
    assert reservation.state == Reservation.CONFIRMED
    assert reservation.approver == staff_user


@pytest.mark.django_db
def test_user_cannot_modify_or_cancel_manually_confirmed_reservation(user_api_client, detail_url, reservation,
                                                                     reservation_data_extra, resource_in_unit):
    resource_in_unit.need_manual_confirmation = True
    resource_in_unit.reservation_metadata_set = ReservationMetadataSet.objects.get(name='default')
    resource_in_unit.save()

    response = user_api_client.put(detail_url, data=reservation_data_extra)
    assert response.status_code == 403

    response = user_api_client.delete(detail_url)
    assert response.status_code == 403


@pytest.mark.parametrize('username, expected_visibility', [
    (None, False),  # unauthenticated user
    ('test_user', True),  # own reservation
    ('test_user2', False),  # someone else's reservation
    ('test_staff_user', True)  # staff
])
@pytest.mark.django_db
def test_extra_fields_visibility_for_different_user_types(api_client, user, user2, staff_user, list_url, detail_url,
                                                          reservation, resource_in_unit, username, expected_visibility):
    resource_in_unit.need_manual_confirmation = True
    resource_in_unit.reservation_metadata_set = ReservationMetadataSet.objects.get(name='default')
    resource_in_unit.save()
    if username:
        api_client.force_authenticate(user=User.objects.get(username=username))

    for url in (list_url, detail_url):
        response = api_client.get(url)
        assert response.status_code == 200
        reservation_data = response.data['results'][0] if 'results' in response.data else response.data
        for field_name in DEFAULT_RESERVATION_EXTRA_FIELDS:
            assert (field_name in reservation_data) is expected_visibility


@pytest.mark.parametrize('state', [
    Reservation.CANCELLED,
    Reservation.DENIED
])
@pytest.mark.django_db
def test_denied_and_cancelled_reservations_not_active(user_api_client, reservation, reservation_data, list_url,
                                                      resource_in_unit, state):
    reservation.state = state
    reservation.save()

    # test reservation max limit
    response = user_api_client.post(list_url, data=reservation_data)
    assert response.status_code == 201

    # test overlapping reservation
    resource_in_unit.max_reservations_per_user = 2
    resource_in_unit.save()
    reservation_data['begin'] = reservation.begin
    reservation_data['end'] = reservation.end
    response = user_api_client.post(list_url, data=reservation_data)
    assert response.status_code == 201


@pytest.mark.django_db
def test_cannot_make_reservation_in_the_past(user_api_client, reservation_data, list_url):
    reservation_data.update(
        begin='2010-04-04T11:00:00+02:00',
        end='2010-04-04T12:00:00+02:00'
    )
    response = user_api_client.post(list_url, data=reservation_data, HTTP_ACCEPT_LANGUAGE='en')
    assert response.status_code == 400
    assert_non_field_errors_contain(response, 'past')


@pytest.mark.django_db
def test_need_manual_confirmation_filter(user_api_client, user, list_url, reservation, other_resource):
    other_resource.need_manual_confirmation = True
    other_resource.reservation_metadata_set = ReservationMetadataSet.objects.get(name='default')
    other_resource.save()
    reservation_needing_confirmation = Reservation.objects.create(
        resource=other_resource,
        begin='2115-04-05T09:00:00+02:00',
        end='2115-04-05T10:00:00+02:00',
        user=user,
    )

    # no filter, expect both reservations
    response = user_api_client.get(list_url)
    assert response.status_code == 200
    reservation_ids = set([res['id'] for res in response.data['results']])
    assert reservation_ids == {reservation.id, reservation_needing_confirmation.id}

    # filter false, expect only first reservation
    response = user_api_client.get('%s%s' % (list_url, '?need_manual_confirmation=false'))
    assert response.status_code == 200
    reservation_ids = set([res['id'] for res in response.data['results']])
    assert reservation_ids == {reservation.id}

    # filter true, expect only second reservation
    response = user_api_client.get('%s%s' % (list_url, '?need_manual_confirmation=true'))
    assert response.status_code == 200
    reservation_ids = set([res['id'] for res in response.data['results']])
    assert reservation_ids == {reservation_needing_confirmation.id}


@pytest.mark.parametrize('state_filter, expected_states', [
    ('', ['requested', 'confirmed', 'denied', 'cancelled']),
    ('?state=requested', ['requested']),
    ('?state=confirmed,requested', ['confirmed', 'requested']),
    ('?state=confirmed,   requested    ,', ['confirmed', 'requested'])
])
@pytest.mark.django_db
def test_state_filters(user_api_client, user, list_url, reservations_in_all_states, state_filter, expected_states):
    response = user_api_client.get('%s%s' % (list_url, state_filter))
    assert response.status_code == 200
    reservation_ids = set([res['id'] for res in response.data['results']])
    assert reservation_ids == set(reservations_in_all_states[state].id for state in expected_states)


@override_settings(RESPA_MAILS_ENABLED=True)
@pytest.mark.django_db
def test_reservation_mails(staff_api_client, staff_user, user_api_client, test_unit2, list_url, reservation_data_extra):
    resource = Resource.objects.get(id=reservation_data_extra['resource'])
    resource.need_manual_confirmation = True
    resource.reservation_metadata_set = ReservationMetadataSet.objects.get(name='default')
    resource.save()
    assign_perm('can_approve_reservation', staff_user, resource.unit)

    # create other staff user who should not receive mails because he doesn't have permission to the right unit
    other_official = get_user_model().objects.create(
        username='other_unit_official',
        first_name='Ozzy',
        last_name='Official',
        email='ozzy@test_unit2.com',
        is_staff=True,
        preferred_language='en'
    )
    assign_perm('can_approve_reservation', other_official, test_unit2)

    # test REQUESTED
    reservation_data_extra['state'] = Reservation.REQUESTED
    response = user_api_client.post(list_url, data=reservation_data_extra, format='json')
    assert response.status_code == 201

    # 2 mails should be sent, one to the customer, and one to the staff user who can approve the reservation
    # (and no mail for the other staff user)
    assert len(mail.outbox) == 2
    check_received_mail_exists(
        "You've made a preliminary reservation",
        reservation_data_extra['reserver_email_address'],
        'made a preliminary reservation',
        clear_outbox=False
    )
    check_received_mail_exists(
        'Reservation requested',
        staff_user.email,
        'A new preliminary reservation has been made'
    )

    detail_url = '%s%s/' % (list_url, response.data['id'])

    # test DENIED
    reservation_data_extra['state'] = Reservation.DENIED
    response = staff_api_client.put(detail_url, data=reservation_data_extra, format='json')
    assert response.status_code == 200
    assert len(mail.outbox) == 1
    check_received_mail_exists(
        'Reservation denied',
        reservation_data_extra['reserver_email_address'],
        'has been denied.'
    )

    # test CONFIRMED
    reservation_data_extra['state'] = Reservation.CONFIRMED
    response = staff_api_client.put(detail_url, data=reservation_data_extra, format='json')
    assert response.status_code == 200
    assert len(mail.outbox) == 1
    check_received_mail_exists(
        'Reservation confirmed',
        reservation_data_extra['reserver_email_address'],
        'has been confirmed.',
        clear_outbox=False
    )
    assert 'this resource rocks' in str(mail.outbox[0].message())
    mail.outbox = []

    # test CANCELLED
    reservation_data_extra['state'] = Reservation.CANCELLED
    response = staff_api_client.delete(detail_url, format='json')
    assert response.status_code == 204
    assert len(mail.outbox) == 1
    check_received_mail_exists(
        'Reservation cancelled',
        reservation_data_extra['reserver_email_address'],
        'has been cancelled.'
    )


@pytest.mark.django_db
def test_can_approve_filter(staff_api_client, staff_user, list_url, reservation):
    reservation.resource.need_manual_confirmation = True
    reservation.resource.reservation_metadata_set = ReservationMetadataSet.objects.get(name='default')
    reservation.resource.save()
    reservation.state = Reservation.REQUESTED
    reservation.save()

    response = staff_api_client.get('%s%s' % (list_url, '?can_approve=true'))
    assert response.status_code == 200
    assert len(response.data['results']) == 0

    assign_perm('can_approve_reservation', staff_user, reservation.resource.unit)

    response = staff_api_client.get('%s%s' % (list_url, '?can_approve=true'))
    assert response.status_code == 200
    assert len(response.data['results']) == 1


@pytest.mark.django_db
def test_access_code_cannot_be_set_if_type_none(user_api_client, list_url, resource_in_unit, reservation_data):
    reservation_data['access_code'] = '023543'
    response = user_api_client.post(list_url, data=reservation_data, HTTP_ACCEPT_LANGUAGE='en')
    assert response.status_code == 400
    assert 'This field cannot have a value with this resource' in response.data['access_code']


@pytest.mark.django_db
def test_invalid_pin6_access_code(user_api_client, list_url, resource_in_unit, reservation_data):
    resource_in_unit.access_code_type = Resource.ACCESS_CODE_TYPE_PIN6
    resource_in_unit.save()
    reservation_data['access_code'] = 'xxx'
    reservation_data['resource'] = resource_in_unit.id

    response = user_api_client.post(list_url, data=reservation_data, HTTP_ACCEPT_LANGUAGE='en')
    assert response.status_code == 400
    assert 'Invalid value' in response.data['access_code']


@pytest.mark.django_db
def test_pin6_access_code_is_generated_if_not_set(user_api_client, list_url, resource_in_unit, reservation_data):
    resource_in_unit.access_code_type = Resource.ACCESS_CODE_TYPE_PIN6
    resource_in_unit.save()

    response = user_api_client.post(list_url, data=reservation_data)
    assert response.status_code == 201
    new_reservation = Reservation.objects.get(id=response.data['id'])
    assert re.match('^[0-9]{6}$', new_reservation.access_code)


@pytest.mark.django_db
def test_pin6_access_code_can_be_set(user_api_client, list_url, resource_in_unit, reservation_data):
    resource_in_unit.access_code_type = Resource.ACCESS_CODE_TYPE_PIN6
    resource_in_unit.save()
    reservation_data['access_code'] = '023543'
    reservation_data['resource'] = resource_in_unit.id

    response = user_api_client.post(list_url, data=reservation_data)
    assert response.status_code == 201
    new_reservation = Reservation.objects.get(id=response.data['id'])
    assert new_reservation.access_code == '023543'


@pytest.mark.django_db
def test_pin6_access_code_cannot_be_modified(user_api_client, resource_in_unit, reservation, reservation_data):
    resource_in_unit.access_code_type = Resource.ACCESS_CODE_TYPE_PIN6
    resource_in_unit.save()
    reservation.access_code = '123456'
    reservation.save()
    reservation_data['access_code'] = '654321'

    detail_url = reverse('reservation-detail', kwargs={'pk': reservation.pk})
    response = user_api_client.put(detail_url, data=reservation_data, HTTP_ACCEPT_LANGUAGE='en')
    assert response.status_code == 400
    assert 'This field cannot be changed' in response.data['access_code']


@pytest.mark.parametrize('username, has_perm, expected', [
    ('test_user', False, True),  # own reservation
    ('test_user2', False, False),  # someone else's reservation
    ('test_user2', True, True),  # someone else's reservation but having the permission
    ('test_staff_user', False, True)  # staff
])
@pytest.mark.django_db
def test_access_code_visibility(user, user2, staff_user, api_client, resource_in_unit, reservation, username, has_perm,
                                expected):
    resource_in_unit.access_code_type = Resource.ACCESS_CODE_TYPE_PIN6
    resource_in_unit.save()
    reservation.access_code = '123456'
    reservation.save()
    detail_url = reverse('reservation-detail', kwargs={'pk': reservation.pk})

    current_user = User.objects.get(username=username)
    if has_perm:
        assign_perm('can_view_reservation_access_code', current_user, resource_in_unit.unit)
    api_client.force_authenticate(current_user)

    response = api_client.get(detail_url)
    assert response.status_code == 200
    if expected:
        assert response.data['access_code'] == '123456'
    else:
        assert 'access_code' not in response.data


@override_settings(RESPA_MAILS_ENABLED=True)
@pytest.mark.django_db
def test_reservation_created_with_access_code_mail(user_api_client, user, resource_in_unit, list_url, reservation_data):

    # The mail should not be sent if access code type is none
    response = user_api_client.post(list_url, data=reservation_data)
    assert response.status_code == 201
    assert len(mail.outbox) == 0

    reservation_data['access_code'] = '007007'
    resource_in_unit.access_code_type = Resource.ACCESS_CODE_TYPE_PIN6
    resource_in_unit.save()
    Reservation.objects.get(id=response.data['id']).delete()

    response = user_api_client.post(list_url, data=reservation_data)
    assert response.status_code == 201
    check_received_mail_exists(
        'Reservation created',
        user.email,
        'Your access code for the resource: 007007',
    )

    # Verify that modifying the reservation doesn't trigger the mail
    reservation_data['end'] = '2115-04-04T12:00:00+02:00'
    detail_url = reverse('reservation-detail', kwargs={'pk': response.data['id']})
    response = user_api_client.put(detail_url, data=reservation_data)
    assert response.status_code == 200
    assert len(mail.outbox) == 0


@freeze_time('2016-10-25')
@pytest.mark.django_db
def test_reservation_reservable_before(user_api_client, resource_in_unit, list_url, reservation_data):
    resource_in_unit.reservable_days_in_advance = 10
    resource_in_unit.save()

    reservation_data['begin'] = timezone.now().replace(hour=12, minute=0, second=0) + datetime.timedelta(days=11)
    reservation_data['end'] = timezone.now().replace(hour=13, minute=0, second=0) + datetime.timedelta(days=11)

    response = user_api_client.post(list_url, data=reservation_data)
    assert response.status_code == 400
    assert_non_field_errors_contain(response, 'The resource is reservable only before')

    reservation_data['begin'] = timezone.now().replace(hour=12, minute=0, second=0) + datetime.timedelta(days=9)
    reservation_data['end'] = timezone.now().replace(hour=13, minute=0, second=0) + datetime.timedelta(days=9)

    response = user_api_client.post(list_url, data=reservation_data)
    assert response.status_code == 201


@pytest.mark.django_db
def test_reservation_metadata_set(user_api_client, reservation, list_url, reservation_data):
    detail_url = reverse('reservation-detail', kwargs={'pk': reservation.pk})
    field_1 = ReservationMetadataField.objects.get(field_name='reserver_name')
    field_2 = ReservationMetadataField.objects.get(field_name='reserver_phone_number')
    metadata_set = ReservationMetadataSet.objects.create(
        name='test_set',

    )
    metadata_set.supported_fields = [field_1, field_2]
    metadata_set.required_fields = [field_1]

    reservation.resource.reservation_metadata_set = metadata_set
    reservation.resource.save(update_fields=('reservation_metadata_set',))
    reservation_data['resource'] = reservation.resource.pk

    response = user_api_client.put(detail_url, data=reservation_data, HTTP_ACCEPT_LANGUAGE='en')
    assert response.status_code == 400
    assert 'This field is required.' in response.data['reserver_name']

    reservation_data['reserver_name'] = 'Mr. Reserver'
    reservation_data['reserver_phone_number'] = '0700-555555'
    reservation_data['reserver_address_street'] = 'ignored street 7'

    response = user_api_client.put(detail_url, data=reservation_data)
    assert response.status_code == 200

    reservation.refresh_from_db()
    assert reservation.reserver_name == 'Mr. Reserver'
    assert reservation.reserver_phone_number == '0700-555555'
    assert reservation.reserver_address_street != 'ignored street 7'


@pytest.mark.django_db
def test_detail_endpoint_does_not_need_all_true_filter(user_api_client, user, resource_in_unit):
    reservation_in_the_past = Reservation.objects.create(
        resource=resource_in_unit,
        begin='2005-04-04T09:00:00+02:00',
        end='2005-04-04T10:00:00+02:00',
        user=user,
    )

    detail_url = reverse('reservation-detail', kwargs={'pk': reservation_in_the_past.pk})
    response = user_api_client.get(detail_url)
    assert response.status_code == 200
