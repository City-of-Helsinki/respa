import datetime
import pytest
from copy import deepcopy
from django.urls import reverse
from django.contrib.gis.geos import Point
from django.utils import timezone
from freezegun import freeze_time
from guardian.shortcuts import assign_perm, remove_perm
from ..enums import UnitAuthorizationLevel, UnitGroupAuthorizationLevel

from resources.models import (Day, Equipment, Period, Reservation, ReservationMetadataSet, ResourceEquipment,
                              ResourceType, Unit, UnitAuthorization, UnitGroup)
from .utils import assert_response_objects, check_only_safe_methods_allowed


@pytest.fixture
def list_url():
    return reverse('resource-list')


def get_detail_url(resource):
    return '%s%s/' % (reverse('resource-list'), resource.pk)


@pytest.mark.django_db
@pytest.fixture
def detail_url(resource_in_unit):
    return reverse('resource-detail', kwargs={'pk': resource_in_unit.pk})


def _check_permissions_dict(api_client, resource, is_admin, can_make_reservations,
                            can_ignore_opening_hours):
    """
    Check that user permissions returned from resource endpoint contain correct values
    for given user and resource. api_client should have the user authenticated.
    """

    url = reverse('resource-detail', kwargs={'pk': resource.pk})
    response = api_client.get(url)
    assert response.status_code == 200
    permissions = response.data['user_permissions']
    assert len(permissions) == 3
    assert permissions['is_admin'] == is_admin
    assert permissions['can_make_reservations'] == can_make_reservations
    assert permissions['can_ignore_opening_hours'] == can_ignore_opening_hours


@pytest.mark.django_db
def test_disallowed_methods(all_user_types_api_client, list_url, detail_url):
    """
    Tests that only safe methods are allowed to unit list and detail endpoints.
    """
    check_only_safe_methods_allowed(all_user_types_api_client, (list_url, detail_url))


@pytest.mark.django_db
def test_user_permissions_in_resource_endpoint(api_client, resource_in_unit, user, group):
    """
    Tests that resource endpoint returns a permissions dict with correct values.
    """
    api_client.force_authenticate(user=user)

    # normal user, reservable = True
    _check_permissions_dict(api_client, resource_in_unit, is_admin=False,
                            can_make_reservations=True, can_ignore_opening_hours=False)

    # normal user, reservable = False
    resource_in_unit.reservable = False
    resource_in_unit.save()
    _check_permissions_dict(api_client, resource_in_unit, is_admin=False,
                            can_make_reservations=False, can_ignore_opening_hours=False)

    # admin, reservable = False
    user.is_general_admin = True
    user.save()
    api_client.force_authenticate(user=user)
    _check_permissions_dict(api_client, resource_in_unit, is_admin=True,
                            can_make_reservations=True, can_ignore_opening_hours=True)
    user.is_general_admin = False
    user.save()

    # user has explicit permission to make reservation
    user.groups.add(group)
    assign_perm('unit:can_make_reservations', group, resource_in_unit.unit)
    api_client.force_authenticate(user=user)
    _check_permissions_dict(api_client, resource_in_unit, is_admin=False,
                            can_make_reservations=True, can_ignore_opening_hours=False)
    remove_perm('unit:can_make_reservations', group, resource_in_unit.unit)

    resource_group = resource_in_unit.groups.create(name='rg1')
    assign_perm('group:can_make_reservations', group, resource_group)
    api_client.force_authenticate(user=user)
    _check_permissions_dict(api_client, resource_in_unit, is_admin=False,
                            can_make_reservations=True, can_ignore_opening_hours=False)

    assign_perm('unit:can_ignore_opening_hours', group, resource_in_unit.unit)
    api_client.force_authenticate(user=user)
    _check_permissions_dict(api_client, resource_in_unit, is_admin=False,
                            can_make_reservations=True, can_ignore_opening_hours=True)


@pytest.mark.django_db
def test_non_public_resource_visibility(api_client, resource_in_unit, user, staff_user):
    """
    Tests that non-public resources are not returned for non-staff.
    """

    resource_in_unit.public = False
    resource_in_unit.save()

    url = reverse('resource-detail', kwargs={'pk': resource_in_unit.pk})
    response = api_client.get(url)
    assert response.status_code == 404

    # Unauthenticated
    url = reverse('resource-list')
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.data['count'] == 0

    # Authenticated as non-staff
    api_client.force_authenticate(user=user)
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.data['count'] == 0

    # Authenticated as non-admin staff
    user.is_staff = True
    user.save()
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.data['count'] == 0

    # Authenticated as admin
    user.is_general_admin = True
    user.save()
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.data['count'] == 1
    url = reverse('resource-detail', kwargs={'pk': resource_in_unit.pk})
    response = api_client.get(url)
    assert response.status_code == 200

    # Authenticated as unit manager
    user.is_general_admin = False
    user.save()
    user.unit_authorizations.create(
        authorized=staff_user,
        level=UnitAuthorizationLevel.manager,
        subject=resource_in_unit.unit
    )
    user.save()
    url = reverse('resource-list')
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.data['count'] == 1
    assert Unit.objects.managed_by(user).values_list('id', flat=True)[0] == response.data['results'][0]['unit']

    # Authenticated as unit admin
    user.unit_authorizations.create(
        authorized=staff_user,
        level=UnitAuthorizationLevel.admin,
        subject=resource_in_unit.unit
    )
    user.save()
    url = reverse('resource-list')
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.data['count'] == 1
    assert Unit.objects.managed_by(user).values_list('id', flat=True)[0] == response.data['results'][0]['unit']

    # Authenticated as unit group admin
    user.unit_authorizations.all().delete()
    unit_group = UnitGroup.objects.create(name='foo')
    unit_group.members.add(resource_in_unit.unit)
    user.unit_group_authorizations.create(
        authorized=staff_user,
        level=UnitGroupAuthorizationLevel.admin,
        subject=unit_group
    )
    user.save()
    url = reverse('resource-list')
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.data['count'] == 1
    assert Unit.objects.managed_by(user).values_list('id', flat=True)[0] == response.data['results'][0]['unit']


@pytest.mark.django_db
def test_api_resource_geo_queries(api_client, resource_in_unit):
    id_base = resource_in_unit.pk
    res = resource_in_unit

    res.location = None
    res.save()

    res.pk = id_base + "r2"
    res.location = Point(24, 60, srid=4326)
    res.save()

    res.pk = id_base + "r3"
    res.location = Point(25, 60, srid=4326)
    res.save()

    unit = resource_in_unit.unit
    unit.location = None
    unit.save()

    unit.pk = unit.pk + "u2"
    unit.location = Point(24, 61, srid=4326)
    unit.save()
    res.pk = id_base + "r4"
    res.location = None
    res.unit = unit
    res.save()

    base_url = reverse('resource-list')

    response = api_client.get(base_url)
    assert response.data['count'] == 4
    results = response.data['results']
    assert 'distance' not in results[0]

    url = base_url + '?lat=60&lon=24'
    response = api_client.get(url)
    assert response.data['count'] == 4
    results = response.data['results']
    assert results[0]['id'].endswith('r2')
    assert results[0]['distance'] == 0
    assert results[1]['id'].endswith('r3')
    assert results[1]['distance'] == 55597
    assert results[2]['distance'] == 111195
    assert 'distance' not in results[3]

    # Check that location is inherited from the resource's unit
    url = base_url + '?lat=61&lon=25&distance=100000'
    response = api_client.get(url)
    assert response.data['count'] == 1
    results = response.data['results']
    assert results[0]['id'].endswith('r4')
    assert results[0]['distance'] == 53907


@pytest.mark.django_db
def test_resource_favorite(staff_api_client, staff_user, resource_in_unit):
    url = '%sfavorite/' % get_detail_url(resource_in_unit)

    response = staff_api_client.post(url)
    assert response.status_code == 201
    assert resource_in_unit in staff_user.favorite_resources.all()

    response = staff_api_client.post(url)
    assert response.status_code == 304
    assert resource_in_unit in staff_user.favorite_resources.all()


@pytest.mark.django_db
def test_resource_favorite_non_official(user_api_client, user, resource_in_unit):
    url = '%sfavorite/' % get_detail_url(resource_in_unit)

    response = user_api_client.post(url)
    assert response.status_code == 201
    assert resource_in_unit in user.favorite_resources.all()

    response = user_api_client.post(url)
    assert response.status_code == 304
    assert resource_in_unit in user.favorite_resources.all()


@pytest.mark.django_db
def test_resource_unfavorite(staff_api_client, staff_user, resource_in_unit):
    url = '%sunfavorite/' % get_detail_url(resource_in_unit)

    response = staff_api_client.post(url)
    assert response.status_code == 304

    staff_user.favorite_resources.add(resource_in_unit)

    response = staff_api_client.post(url)
    assert response.status_code == 204
    assert resource_in_unit not in staff_user.favorite_resources.all()


@pytest.mark.django_db
def test_resource_unfavorite_non_official(user_api_client, user, resource_in_unit):
    url = '%sunfavorite/' % get_detail_url(resource_in_unit)

    response = user_api_client.post(url)
    assert response.status_code == 304

    user.favorite_resources.add(resource_in_unit)

    response = user_api_client.post(url)
    assert response.status_code == 204
    assert resource_in_unit not in user.favorite_resources.all()


@pytest.mark.django_db
def test_is_favorite_field(api_client, staff_api_client, staff_user, resource_in_unit):
    url = get_detail_url(resource_in_unit)

    response = api_client.get(url)
    assert response.status_code == 200
    assert response.data['is_favorite'] is False

    response = staff_api_client.get(url)
    assert response.status_code == 200
    assert response.data['is_favorite'] is False

    staff_user.favorite_resources.add(resource_in_unit)
    response = staff_api_client.get(url)
    assert response.status_code == 200
    assert response.data['is_favorite'] is True


@pytest.mark.django_db
def test_filtering_by_is_favorite(list_url, api_client, staff_api_client, staff_user, resource_in_unit,
                                  resource_in_unit2):
    staff_user.favorite_resources.add(resource_in_unit)

    # anonymous users don't need the filter atm, just check that using the filter doesn't cause any errors
    response = api_client.get('%s?is_favorite=true' % list_url)
    assert response.status_code == 200
    assert response.data['count'] == 0

    response = staff_api_client.get('%s?is_favorite=true' % list_url)
    assert response.status_code == 200
    assert response.data['count'] == 1
    assert response.data['results'][0]['id'] == resource_in_unit.id

    response = staff_api_client.get('%s?is_favorite=false' % list_url)
    assert response.status_code == 200
    assert response.data['count'] == 1
    assert response.data['results'][0]['id'] == resource_in_unit2.id


@pytest.mark.django_db
def test_api_resource_terms_of_use(api_client, resource_in_unit, detail_url):
    response = api_client.get(detail_url)
    assert response.status_code == 200

    generic_terms = response.data['generic_terms']
    specific_terms = response.data['specific_terms']

    assert set(generic_terms) == {'fi', 'en'}
    assert generic_terms['fi'] == 'kaikki on kielletty'
    assert generic_terms['en'] == 'everything is forbidden'

    assert set(specific_terms) == {'fi', 'en'}
    assert specific_terms['fi'] == 'spesifiset käyttöehdot'
    assert specific_terms['en'] == 'specific terms of use'


@pytest.mark.django_db
def test_price_per_hour_fields(api_client, resource_in_unit, detail_url):
    resource_in_unit.min_price_per_hour = '5.05'
    resource_in_unit.max_price_per_hour = None
    resource_in_unit.save()

    response = api_client.get(detail_url)
    assert response.status_code == 200

    assert response.data['min_price_per_hour'] == '5.05'
    assert response.data['max_price_per_hour'] is None


@freeze_time('2016-10-25')
@pytest.mark.django_db
def test_reservable_in_advance_fields(api_client, resource_in_unit, test_unit, detail_url):
    response = api_client.get(detail_url)
    assert response.status_code == 200

    # the unit and the resource both have days None, so expect None in the fields
    assert response.data['reservable_max_days_in_advance'] is None
    assert response.data['reservable_before'] is None

    test_unit.reservable_max_days_in_advance = 5
    test_unit.save()

    response = api_client.get(detail_url)
    assert response.status_code == 200

    # only the unit has days set, expect those on the resource
    assert response.data['reservable_max_days_in_advance'] == 5
    before = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=6)
    assert response.data['reservable_before'] == before

    resource_in_unit.reservable_max_days_in_advance = 10
    resource_in_unit.save()

    response = api_client.get(detail_url)
    assert response.status_code == 200

    # both the unit and the resource have days set, expect the resource's days to override the unit's days
    assert response.data['reservable_max_days_in_advance'] == 10
    before = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=11)
    assert response.data['reservable_before'] == before


@pytest.mark.django_db
def test_resource_group_filter(api_client, resource_in_unit, resource_in_unit2, resource_group, resource_group2,
                               list_url):
    extra_unit = deepcopy(resource_in_unit)
    extra_unit.id = None
    extra_unit.save()

    # no group
    response = api_client.get(list_url)
    assert response.status_code == 200
    assert len(response.data['results']) == 3

    # one group
    response = api_client.get('%s?resource_group=%s' % (list_url, resource_group.identifier))
    assert response.status_code == 200
    assert set(r['id'] for r in response.data['results']) == {resource_in_unit.id}

    # multiple groups
    response = api_client.get(
        '%s?resource_group=%s,%s' % (list_url, resource_group.identifier, resource_group2.identifier)
    )
    assert response.status_code == 200
    assert set(r['id'] for r in response.data['results']) == {resource_in_unit.id, resource_in_unit2.id}


@pytest.mark.django_db
def test_include_unit_detail(api_client, resource_in_unit, list_url):
    response = api_client.get(list_url + '?include=unit_detail')
    assert response.status_code == 200
    assert response.json()['results'][0]['unit']['id'] == resource_in_unit.unit.id


@pytest.mark.django_db
def test_reservation_extra_fields(api_client, resource_in_unit):
    default_set = ReservationMetadataSet.objects.get(name='default')
    resource_in_unit.reservation_metadata_set = default_set
    resource_in_unit.save(update_fields=('reservation_metadata_set',))

    response = api_client.get(get_detail_url(resource_in_unit))
    assert response.status_code == 200

    supported_fields = set(default_set.supported_fields.values_list('field_name', flat=True))
    assert set(response.data['supported_reservation_extra_fields']) == supported_fields

    required_fields = set(default_set.required_fields.values_list('field_name', flat=True))
    assert set(response.data['required_reservation_extra_fields']) == required_fields


@pytest.mark.django_db
def test_resource_type_filter(api_client, resource_in_unit, resource_in_unit2, resource_in_unit3, list_url):
    type_1 = ResourceType.objects.create(name='type_1', main_type='space')
    type_2 = ResourceType.objects.create(name='type_2', main_type='space')
    extra_type = ResourceType.objects.create(name='extra_type', main_type='space')

    resource_in_unit.type = type_1
    resource_in_unit.save()
    resource_in_unit2.type = type_2
    resource_in_unit2.save()
    resource_in_unit3.type = extra_type
    resource_in_unit3.save()

    response = api_client.get(list_url + '?type=%s' % type_1.id)
    assert response.status_code == 200
    assert {resource['id'] for resource in response.data['results']} == {resource_in_unit.id}

    response = api_client.get(list_url + '?type=%s,%s' % (type_1.id, type_2.id))
    assert response.status_code == 200
    assert {resource['id'] for resource in response.data['results']} == {resource_in_unit.id, resource_in_unit2.id}


@pytest.mark.django_db
def test_resource_equipment_filter(api_client, resource_in_unit, resource_in_unit2, resource_in_unit3,
                                   equipment_category, resource_equipment, list_url):
    equipment_1 = Equipment.objects.create(
        name='equipment 1',
        category=equipment_category,
    )
    ResourceEquipment.objects.create(
        equipment=equipment_1,
        resource=resource_in_unit,
        description='resource equipment 1',
    )
    equipment_2 = Equipment.objects.create(
        name='equipment 2',
        category=equipment_category,
    )
    ResourceEquipment.objects.create(
        equipment=equipment_2,
        resource=resource_in_unit2,
        description='resource equipment 2',
    )
    resource_in_unit3.resource_equipment.set([resource_equipment])

    response = api_client.get(list_url + '?equipment=%s' % equipment_1.id)
    assert response.status_code == 200
    assert {resource['id'] for resource in response.data['results']} == {resource_in_unit.id}

    response = api_client.get(list_url + '?equipment=%s,%s' % (equipment_1.id, equipment_2.id))
    assert response.status_code == 200
    assert {resource['id'] for resource in response.data['results']} == {resource_in_unit.id, resource_in_unit2.id}


@pytest.mark.parametrize('filtering, expected_resource_indexes', (
    ({}, [0, 1]),
    ({'available_between': '2115-04-08T08:00:00+02:00,2115-04-08T10:00:00+02:00'}, [0, 1]),
    ({'available_between': '2115-04-08T08:00:00+02:00,2115-04-08T10:00:01+02:00'}, [1]),
    ({'available_between': '2115-04-08T10:59:59+02:00,2115-04-08T12:00:00+02:00'}, [1]),
    ({'available_between': '2115-04-08T10:59:59+02:00,2115-04-08T12:00:01+02:00'}, []),
    ({'available_between': '2115-04-08T13:00:00+02:00,2115-04-08T18:00:00+02:00'}, [0, 1]),
))
@pytest.mark.django_db
def test_resource_available_between_filter_reservations(user_api_client, list_url, user, resource_in_unit,
                                                        resource_in_unit2, filtering, expected_resource_indexes):
    resources = (resource_in_unit, resource_in_unit2)
    Reservation.objects.create(
        resource=resource_in_unit,
        begin='2115-04-08T10:00:00+02:00',
        end='2115-04-08T11:00:00+02:00',
        user=user,
    )
    Reservation.objects.create(
        resource=resource_in_unit2,
        begin='2115-04-08T12:00:00+02:00',
        end='2115-04-08T13:00:00+02:00',
        user=user,
    )

    # set resources open practically the whole so that opening hours don't intervene in this test
    for resource in resources:
        p1 = Period.objects.create(start=datetime.date(2115, 4, 1),
                                   end=datetime.date(2115, 4, 30),
                                   resource=resource)
        for weekday in range(0, 7):
            Day.objects.create(period=p1, weekday=weekday,
                               opens=datetime.time(0, 0),
                               closes=datetime.time(23, 59))
        resource.update_opening_hours()

    response = user_api_client.get(list_url, filtering)
    assert response.status_code == 200
    assert_response_objects(response, [resources[index] for index in expected_resource_indexes])


@pytest.mark.parametrize('filtering, expected_resource_indexes', (
    ({}, [0, 1]),
    ({'available_between': '2115-04-08T06:00:00+02:00,2115-04-08T07:00:00+02:00'}, []),
    ({'available_between': '2115-04-08T07:59:59+02:00,2115-04-08T16:00:00+02:00'}, []),
    ({'available_between': '2115-04-08T08:00:00+02:00,2115-04-08T16:00:00+02:00'}, [0]),
    ({'available_between': '2115-04-08T08:00:00+02:00,2115-04-08T16:00:01+02:00'}, []),
    ({'available_between': '2115-04-08T12:00:00+02:00,2115-04-08T14:00:00+02:00'}, [0, 1]),
    ({'available_between': '2115-04-14T12:00:00+02:00,2115-04-14T14:00:00+02:00'}, [0]),

))
@pytest.mark.django_db
def test_resource_available_between_filter_opening_hours(user_api_client, list_url, resource_in_unit, resource_in_unit2,
                                                         filtering, expected_resource_indexes):
    resources = (resource_in_unit, resource_in_unit2)

    p1 = Period.objects.create(start=datetime.date(2115, 4, 1),
                               end=datetime.date(2115, 4, 30),
                               resource=resource_in_unit)
    for weekday in range(0, 7):
        Day.objects.create(period=p1, weekday=weekday,
                           opens=datetime.time(8, 0),
                           closes=datetime.time(16, 0))

    p1 = Period.objects.create(start=datetime.date(2115, 4, 1),
                               end=datetime.date(2115, 4, 30),
                               resource=resource_in_unit2)
    for weekday in range(0, 6):
        Day.objects.create(period=p1, weekday=weekday,
                           opens=datetime.time(12, 0),
                           closes=datetime.time(14, 0))

    resource_in_unit.update_opening_hours()
    resource_in_unit2.update_opening_hours()

    response = user_api_client.get(list_url, filtering)
    assert response.status_code == 200
    assert_response_objects(response, [resources[index] for index in expected_resource_indexes])


@pytest.mark.django_db
def test_resource_available_between_filter_constraints(user_api_client, list_url, resource_in_unit):
    response = user_api_client.get(list_url, {
        'available_between': '2115-04-08T00:00:00+02:00'
    })
    assert response.status_code == 400
    assert 'available_between takes two or three comma-separated values.' in str(response.data)

    response = user_api_client.get(list_url, {
        'available_between': '2115-04-08T00:00:00+02:00,100,100,100'
    })
    assert response.status_code == 400
    assert 'available_between takes two or three comma-separated values.' in str(response.data)

    response = user_api_client.get(list_url, {
        'available_between': '2115-04-08T00:00:00+02:00,2115-04-09T00:00:00+02:00'
    })
    assert response.status_code == 400
    assert 'available_between timestamps must be on the same day.' in str(response.data)

    response = user_api_client.get(list_url, {
        'available_between': '2115-04-08T00:00:00+02:00,2115-04-09T00:00:00+02:00,60'
    })
    assert response.status_code == 400
    assert 'available_between timestamps must be on the same day.' in str(response.data)

    response = user_api_client.get(list_url, {
        'available_between': '2115-04-08T00:00:00+02:00,2115-04-08T00:00:00+02:00,xyz'
    })
    assert response.status_code == 400
    assert 'available_between period must be an integer.' in str(response.data)


@pytest.mark.django_db
def test_resource_available_between_considers_inactive_reservations(user_api_client, user, list_url, resource_in_unit):
    p1 = Period.objects.create(start=datetime.date(2115, 4, 1),
                               end=datetime.date(2115, 4, 30),
                               resource=resource_in_unit)
    for weekday in range(0, 7):
        Day.objects.create(period=p1, weekday=weekday,
                           opens=datetime.time(0, 0),
                           closes=datetime.time(23, 59))
    resource_in_unit.update_opening_hours()

    # First no reservations
    params = {'available_between': '2115-04-08T08:00:00+02:00,2115-04-08T16:00:00+02:00'}
    response = user_api_client.get(list_url, params)
    assert response.status_code == 200
    assert_response_objects(response, [resource_in_unit])

    # One confirmed reservation
    rv = Reservation.objects.create(
        resource=resource_in_unit,
        begin='2115-04-08T10:00:00+02:00',
        end='2115-04-08T11:00:00+02:00',
        user=user,
    )
    # Reload the reservation from database to make sure begin and end are
    # datetimes (not strings).
    rv = Reservation.objects.get(id=rv.id)

    params = {'available_between': '2115-04-08T08:00:00+02:00,2115-04-08T16:00:00+02:00'}
    response = user_api_client.get(list_url, params)
    assert response.status_code == 200
    assert_response_objects(response, [])

    # Cancelled reservations should be ignored
    rv.set_state(Reservation.CANCELLED, user)
    response = user_api_client.get(list_url, params)
    assert response.status_code == 200
    assert_response_objects(response, [resource_in_unit])

    # Requested should be taken into account
    rv.set_state(Reservation.REQUESTED, user)
    response = user_api_client.get(list_url, params)
    assert response.status_code == 200
    assert_response_objects(response, [])

    # Denied ignored
    rv.set_state(Reservation.DENIED, user)
    response = user_api_client.get(list_url, params)
    assert response.status_code == 200
    assert_response_objects(response, [resource_in_unit])


@pytest.mark.parametrize('start, end, period, expected', (
    ('00:00', '00:30', 60, []),
    ('06:00', '06:30', 60, []),
    ('06:00', '06:30', 30, [1]),
    ('06:00', '08:30', 60, [1]),
    ('06:00', '08:30', 30, [0, 1]),
    ('09:00', '11:00', 60, [0, 1]),
    ('09:00', '11:00', 120, [1]),
    ('10:00', '12:00', 60, [0, 1]),
    ('10:00', '12:00', 120, [1]),
    ('10:00', '12:00', 180, []),
    ('10:00', '14:00', 120, [1]),
    ('10:00', '15:00', 120, [0, 1]),
    ('12:00', '17:00', 120, [0, 1]),
    ('12:00', '17:00', 180, [0, 1]),
    ('15:00', '17:00', 60, [0, 1]),
    ('15:00', '17:00', 120, [1]),
    ('17:00', '18:00', 60, [1]),
    ('17:00', '18:00', 120, []),
    ('00:00', '23:00', 180, [0, 1]),
    ('00:00', '23:00', 240, [1]),
))
@pytest.mark.django_db
def test_available_between_with_period(list_url, resource_in_unit, resource_in_unit2, resource_in_unit3, user,
                                       user_api_client, start, end, period, expected):

    # resource_in_unit is open 8-16, resource_in_unit2 00:00 - 23:59
    p1 = Period.objects.create(start=datetime.date(2115, 4, 1),
                               end=datetime.date(2115, 4, 8),
                               resource=resource_in_unit)
    p2 = Period.objects.create(start=datetime.date(2115, 4, 1),
                               end=datetime.date(2115, 4, 8),
                               resource=resource_in_unit2)
    for weekday in range(0, 7):
        Day.objects.create(period=p1, weekday=weekday,
                           opens=datetime.time(8, 0),
                           closes=datetime.time(16, 00))
        Day.objects.create(period=p2, weekday=weekday,
                           opens=datetime.time(0, 0),
                           closes=datetime.time(23, 59))
    resource_in_unit.update_opening_hours()
    resource_in_unit2.update_opening_hours()

    Reservation.objects.create(
        resource=resource_in_unit,
        begin='2115-04-08T10:00:00+02:00',
        end='2115-04-08T11:00:00+02:00',
        user=user,
    ),
    Reservation.objects.create(
        resource=resource_in_unit,
        begin='2115-04-08T12:00:00+02:00',
        end='2115-04-08T13:00:00+02:00',
        user=user,
    )

    params = {'available_between': '2115-04-08T{}:00+02:00,2115-04-08T{}:00+02:00,{}'.format(start, end, period)}
    expected_resources = [r for i, r in enumerate([resource_in_unit, resource_in_unit2]) if i in expected]
    response = user_api_client.get(list_url, params)
    assert response.status_code == 200
    assert_response_objects(response, expected_resources)


@pytest.mark.django_db
def test_filtering_free_of_charge(list_url, api_client, resource_in_unit,
                                  resource_in_unit2, resource_in_unit3):
    free_resource = resource_in_unit
    free_resource2 = resource_in_unit2
    not_free_resource = resource_in_unit3

    free_resource.min_price_per_hour = 0
    free_resource.save()
    not_free_resource.min_price_per_hour = 9001
    not_free_resource.save()

    response = api_client.get('{0}?free_of_charge=true'.format(list_url))
    assert response.status_code == 200
    assert_response_objects(response, [free_resource, free_resource2])

    response = api_client.get('{0}?free_of_charge=false'.format(list_url))
    assert response.status_code == 200
    assert_response_objects(response, not_free_resource)


@pytest.mark.django_db
def test_filtering_by_municipality(list_url, api_client, resource_in_unit, test_unit, test_municipality):
    test_unit.municipality = test_municipality
    test_unit.save()

    response = api_client.get('%s?municipality=foo' % list_url)
    assert response.status_code == 200
    assert_response_objects(response, resource_in_unit) 

    response = api_client.get('%s?municipality=bar' % list_url)
    assert response.status_code == 200
    assert_response_objects(response, []) 


@pytest.mark.django_db
def test_order_by_filter(list_url, api_client, resource_in_unit, resource_in_unit2):
    # test resource_name_fi
    resource_in_unit.name_fi, resource_in_unit.name_en, resource_in_unit.name_sv = 'aaa'
    resource_in_unit.save()

    resource_in_unit2.name_fi, resource_in_unit2.name_en, resource_in_unit2.name_sv = 'bbb'
    resource_in_unit2.save()

    response = api_client.get('%s?order_by=resource_name_fi' % list_url)
    assert response.status_code == 200
    assert_response_objects(response, [resource_in_unit, resource_in_unit2])
    assert response.data['results'][0]['name']['fi'] == resource_in_unit.name_fi
    assert response.data['results'][1]['name']['fi'] == resource_in_unit2.name_fi

    response = api_client.get('%s?order_by=-resource_name_fi' % list_url)
    assert response.status_code == 200
    assert_response_objects(response, [resource_in_unit, resource_in_unit2])
    assert response.data['results'][1]['name']['fi'] == resource_in_unit.name_fi
    assert response.data['results'][0]['name']['fi'] == resource_in_unit2.name_fi

    # test resource_name_en
    response = api_client.get('%s?order_by=resource_name_en' % list_url)
    assert response.status_code == 200
    assert_response_objects(response, [resource_in_unit, resource_in_unit2])
    assert response.data['results'][0]['name']['en'] == resource_in_unit.name_en
    assert response.data['results'][1]['name']['en'] == resource_in_unit2.name_en

    response = api_client.get('%s?order_by=-resource_name_en' % list_url)
    assert response.status_code == 200
    assert_response_objects(response, [resource_in_unit, resource_in_unit2])
    assert response.data['results'][1]['name']['en'] == resource_in_unit.name_en
    assert response.data['results'][0]['name']['en'] == resource_in_unit2.name_en

    # test resource_name_sv
    response = api_client.get('%s?order_by=resource_name_sv' % list_url)
    assert response.status_code == 200
    assert_response_objects(response, [resource_in_unit, resource_in_unit2])
    assert response.data['results'][0]['name']['sv'] == resource_in_unit.name_sv
    assert response.data['results'][1]['name']['sv'] == resource_in_unit2.name_sv

    response = api_client.get('%s?order_by=-resource_name_sv' % list_url)
    assert response.status_code == 200
    assert_response_objects(response, [resource_in_unit, resource_in_unit2])
    assert response.data['results'][1]['name']['sv'] == resource_in_unit.name_sv
    assert response.data['results'][0]['name']['sv'] == resource_in_unit2.name_sv

    # test unit_name_fi
    resource_in_unit.unit.name_fi, resource_in_unit.unit.name_en, resource_in_unit.unit.name_sv = 'aaa'
    resource_in_unit.unit.save()

    resource_in_unit2.unit.name_fi, resource_in_unit2.unit.name_en, resource_in_unit2.unit.name_sv = 'bbb'
    resource_in_unit2.unit.save()

    response = api_client.get('%s?order_by=unit_name_fi' % list_url)
    assert response.status_code == 200
    assert_response_objects(response, [resource_in_unit, resource_in_unit2])
    assert response.data['results'][0]['unit'] == resource_in_unit.unit.id
    assert response.data['results'][1]['unit'] == resource_in_unit2.unit.id

    response = api_client.get('%s?order_by=-unit_name_fi' % list_url)
    assert response.status_code == 200
    assert_response_objects(response, [resource_in_unit, resource_in_unit2])
    assert response.data['results'][1]['unit'] == resource_in_unit.unit.id
    assert response.data['results'][0]['unit'] == resource_in_unit2.unit.id

    # test unit_name_en
    response = api_client.get('%s?order_by=unit_name_en' % list_url)
    assert response.status_code == 200
    assert_response_objects(response, [resource_in_unit, resource_in_unit2])
    assert response.data['results'][0]['unit'] == resource_in_unit.unit.id
    assert response.data['results'][1]['unit'] == resource_in_unit2.unit.id

    response = api_client.get('%s?order_by=-unit_name_en' % list_url)
    assert response.status_code == 200
    assert_response_objects(response, [resource_in_unit, resource_in_unit2])
    assert response.data['results'][1]['unit'] == resource_in_unit.unit.id
    assert response.data['results'][0]['unit'] == resource_in_unit2.unit.id

    # test unit_name_sv
    response = api_client.get('%s?order_by=unit_name_sv' % list_url)
    assert response.status_code == 200
    assert_response_objects(response, [resource_in_unit, resource_in_unit2])
    assert response.data['results'][0]['unit'] == resource_in_unit.unit.id
    assert response.data['results'][1]['unit'] == resource_in_unit2.unit.id

    response = api_client.get('%s?order_by=-unit_name_sv' % list_url)
    assert response.status_code == 200
    assert_response_objects(response, [resource_in_unit, resource_in_unit2])
    assert response.data['results'][1]['unit'] == resource_in_unit.unit.id
    assert response.data['results'][0]['unit'] == resource_in_unit2.unit.id

    # test resource type_fi
    resource_in_unit.type = ResourceType(id='foo', main_type='foo', name_fi='aaaa')
    resource_in_unit.type.save()
    resource_in_unit.save()

    resource_in_unit2.type = ResourceType(id='foo', main_type='foo', name_fi='bbbb')
    resource_in_unit2.type.save()
    resource_in_unit2.save()

    response = api_client.get('%s?order_by=type_name_fi' % list_url)
    assert response.status_code == 200
    assert_response_objects(response, [resource_in_unit, resource_in_unit2])
    assert response.data['results'][0]['type']['id'] == resource_in_unit.type.id
    assert response.data['results'][1]['type']['id'] == resource_in_unit2.type.id

    response = api_client.get('%s?order_by=-type_name_fi' % list_url)
    assert response.status_code == 200
    assert_response_objects(response, [resource_in_unit, resource_in_unit2])
    assert response.data['results'][1]['type']['id'] == resource_in_unit.type.id
    assert response.data['results'][0]['type']['id'] == resource_in_unit2.type.id


    # test resource type_en
    resource_in_unit.type = ResourceType(id='foo', main_type='foo', name_en='aaaa')
    resource_in_unit.type.save()
    resource_in_unit.save()

    resource_in_unit2.type = ResourceType(id='foo', main_type='foo', name_en='bbbb')
    resource_in_unit2.type.save()
    resource_in_unit2.save()

    response = api_client.get('%s?order_by=type_name_en' % list_url)
    assert response.status_code == 200
    assert_response_objects(response, [resource_in_unit, resource_in_unit2])
    assert response.data['results'][0]['type']['id'] == resource_in_unit.type.id
    assert response.data['results'][1]['type']['id'] == resource_in_unit2.type.id

    response = api_client.get('%s?order_by=-type_name_en' % list_url)
    assert response.status_code == 200
    assert_response_objects(response, [resource_in_unit, resource_in_unit2])
    assert response.data['results'][1]['type']['id'] == resource_in_unit.type.id
    assert response.data['results'][0]['type']['id'] == resource_in_unit2.type.id


    # test resource type_sv
    resource_in_unit.type = ResourceType(id='foo', main_type='foo', name_sv='aaaa')
    resource_in_unit.type.save()
    resource_in_unit.save()

    resource_in_unit2.type = ResourceType(id='foo', main_type='foo', name_sv='bbbb')
    resource_in_unit2.type.save()
    resource_in_unit2.save()

    response = api_client.get('%s?order_by=type_name_sv' % list_url)
    assert response.status_code == 200
    assert_response_objects(response, [resource_in_unit, resource_in_unit2])
    assert response.data['results'][0]['type']['id'] == resource_in_unit.type.id
    assert response.data['results'][1]['type']['id'] == resource_in_unit2.type.id

    response = api_client.get('%s?order_by=-type_name_sv' % list_url)
    assert response.status_code == 200
    assert_response_objects(response, [resource_in_unit, resource_in_unit2])
    assert response.data['results'][1]['type']['id'] == resource_in_unit.type.id
    assert response.data['results'][0]['type']['id'] == resource_in_unit2.type.id

    # test resource people capacity
    resource_in_unit.people_capacity = 1
    resource_in_unit.save()

    resource_in_unit2.people_capacity = 50
    resource_in_unit2.save()

    response = api_client.get('%s?order_by=people_capacity' % list_url)
    assert response.status_code == 200
    assert_response_objects(response, [resource_in_unit, resource_in_unit2])
    assert response.data['results'][0]['people_capacity'] == resource_in_unit.people_capacity
    assert response.data['results'][1]['people_capacity'] == resource_in_unit2.people_capacity

    response = api_client.get('%s?order_by=-people_capacity' % list_url)
    assert response.status_code == 200
    assert_response_objects(response, [resource_in_unit, resource_in_unit2])
    assert response.data['results'][1]['people_capacity'] == resource_in_unit.people_capacity
    assert response.data['results'][0]['people_capacity'] == resource_in_unit2.people_capacity
