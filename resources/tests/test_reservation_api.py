import pytest
import datetime
from django.utils import dateparse
from django.core.urlresolvers import reverse
from django.core import mail
from django.test.utils import override_settings
from guardian.shortcuts import assign_perm

from resources.models import Period, Day, Reservation, Resource, RESERVATION_EXTRA_FIELDS
from users.models import User
from .utils import check_disallowed_methods, assert_non_field_errors_contain


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
        'business_id': '1234567-8',
        'number_of_participants': 5000,
        'billing_address_street': 'Pihlajakatu',
        'billing_address_zip': '00001',
        'billing_address_city': 'Tampere',
        'company': 'a very secret association'
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


@override_settings(RESPA_MAILS_ENABLED=True)
@pytest.mark.django_db
def test_reservation_created_or_deleted_by_admin_mails_sent(
        staff_api_client, list_url, reservation_data, user):
    """
    Tests that reservations created and deleted by admins will trigger correct emails for users.
    """

    reservation_data['user'] = {'id': user.uuid}

    # create a new reservation
    response = staff_api_client.post(list_url, data=reservation_data, format='json', HTTP_ACCEPT_LANGUAGE='en')
    assert response.status_code == 201
    assert len(mail.outbox) == 1
    mail_instance = mail.outbox[0]
    assert 'Reservation created' in mail_instance.subject
    assert len(mail_instance.to) == 1
    assert mail_instance.to[0] == user.email
    mail_message = str(mail_instance.message())
    assert 'A new reservation has been created for you' in mail_message
    assert 'Starts: April 4, 2115, 11 a.m.' in mail_message

    mail.outbox = []

    # delete the existing reservation
    detail_url = reverse('reservation-detail', kwargs={'pk': response.data['id']})
    response = staff_api_client.delete(detail_url, data=reservation_data, format='json', HTTP_ACCEPT_LANGUAGE='en')
    assert response.status_code == 204
    assert len(mail.outbox) == 1
    mail_instance = mail.outbox[0]
    assert len(mail_instance.to) == 1
    assert mail_instance.to[0] == user.email
    mail_message = str(mail_instance.message())
    assert 'Your reservation has been deleted' in mail_message
    assert 'The deleted reservation:' in mail_message
    assert 'Starts: April 4, 2115, 11 a.m.' in mail_message


@pytest.mark.parametrize("input,expected", [
    ({'begin': '2115-04-04T09:00:00+02:00'}, 'Starts: April 4, 2115, 9 a.m.'),
    ({'end': '2115-04-04T13:00:00+02:00'}, 'Ends: April 4, 2115, 1 p.m.'),
    ({'resource': 'otherresourceid'}, 'Resource: other resource'),
])
@override_settings(RESPA_MAILS_ENABLED=True)
@pytest.mark.django_db
def test_reservation_modified_by_admin_mail_sent(
        staff_api_client, reservation_data, user, other_resource, detail_url, input, expected):
    """
    Tests that reservations modified by admins will trigger correct emails for users.

    Modifying begin time, end time or resource should trigger a mail.
    """
    reservation_data.update(**input)
    response = staff_api_client.put(detail_url, data=reservation_data, format='json', HTTP_ACCEPT_LANGUAGE='en')
    assert response.status_code == 200
    assert len(mail.outbox) == 1
    mail_instance = mail.outbox[0]
    assert len(mail_instance.to) == 1
    assert mail_instance.to[0] == user.email
    mail_message = str(mail_instance.message())
    assert 'Your reservation has been modified' in mail_message
    assert expected in mail_message


@override_settings(RESPA_MAILS_ENABLED=True)
@pytest.mark.django_db
def test_reservation_modified_by_admin_mails_not_sent(
        staff_api_client, list_url, reservation, reservation_data, user):
    """
    Tests situations where modified by admin mail should not be sent.

    Tested situations:
        * a staff member modifies her own reservations
        * a staff member PUTs a reservation for a user but the reservation isn't actually modified
    """

    # a staff member creates a new reservation for herself, expect no mail
    response = staff_api_client.post(list_url, data=reservation_data, format='json')
    assert response.status_code == 201
    assert len(mail.outbox) == 0

    # a staff member modifies her reservation, expect no mail
    reservation_data['begin'] = dateparse.parse_datetime('2115-04-04T10:00:00+02:00')
    detail_url = reverse('reservation-detail', kwargs={'pk': response.data['id']})
    response = staff_api_client.put(detail_url, data=reservation_data, format='json')
    assert response.status_code == 200
    assert len(mail.outbox) == 0

    # a staff member deletes her reservation, expect no mail
    response = staff_api_client.delete(detail_url, data=reservation_data, format='json')
    assert response.status_code == 204
    assert len(mail.outbox) == 0

    # s staff member PUTs a reservation with no modifications for a user, expect no mail
    reservation_data['user'] = {'id': user.uuid}
    detail_url = reverse('reservation-detail', kwargs={'pk': reservation.id})
    reservation_data['begin'] = '2115-04-04T09:00:00+02:00'  # the same data
    reservation_data['end'] = '2115-04-04T10:00:00+02:00'  # as is in the original reservation
    response = staff_api_client.put(detail_url, data=reservation_data, format='json')
    assert response.status_code == 200
    assert len(mail.outbox) == 0


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
    resource_in_unit.save()

    for url in (list_url, detail_url):
        response = user_api_client.get(url)
        assert response.status_code == 200
        reservation_data = response.data['results'][0] if 'results' in response.data else response.data
        for field_name in RESERVATION_EXTRA_FIELDS:
            assert (field_name in reservation_data) is need_manual_confirmation


@pytest.mark.django_db
def test_extra_fields_required_for_paid_reservations(user_api_client, list_url, resource_in_unit, reservation_data):
    resource_in_unit.need_manual_confirmation = True
    resource_in_unit.save()
    response = user_api_client.post(list_url, data=reservation_data)
    assert response.status_code == 400
    for field_name in RESERVATION_EXTRA_FIELDS:
        assert field_name in response.data


@pytest.mark.django_db
def test_extra_fields_can_be_set_for_paid_reservations(user_api_client, list_url, reservation_data_extra,
                                                      resource_in_unit):
    resource_in_unit.max_reservations_per_user = 2
    resource_in_unit.need_manual_confirmation = True
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
    resource_in_unit.save()
    if username:
        api_client.force_authenticate(user=User.objects.get(username=username))

    for url in (list_url, detail_url):
        response = api_client.get(url)
        assert response.status_code == 200
        reservation_data = response.data['results'][0] if 'results' in response.data else response.data
        for field_name in RESERVATION_EXTRA_FIELDS:
            assert (field_name in reservation_data) is expected_visibility
