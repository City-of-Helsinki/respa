import datetime
import pytest
from django.core.urlresolvers import reverse
from django.contrib.gis.geos import Point
from django.utils import timezone
from freezegun import freeze_time

from .utils import check_only_safe_methods_allowed


@pytest.fixture
def list_url():
    return reverse('resource-list')


def get_detail_url(resource):
    return '%s%s/' % (reverse('resource-list'), resource.pk)


@pytest.mark.django_db
@pytest.fixture
def detail_url(resource_in_unit):
    return reverse('resource-detail', kwargs={'pk': resource_in_unit.pk})


def _check_permissions_dict(api_client, resource, is_admin, can_make_reservation):
    """
    Check that user permissions returned from resource endpoint contain correct values
    for given user and resource. api_client should have the user authenticated.
    """

    url = reverse('resource-detail', kwargs={'pk': resource.pk})
    response = api_client.get(url)
    assert response.status_code == 200
    permissions = response.data['user_permissions']
    assert len(permissions) == 2
    assert permissions['is_admin'] == is_admin
    assert permissions['can_make_reservations'] == can_make_reservation


@pytest.mark.django_db
def test_disallowed_methods(all_user_types_api_client, list_url, detail_url):
    """
    Tests that only safe methods are allowed to unit list and detail endpoints.
    """
    check_only_safe_methods_allowed(all_user_types_api_client, (list_url, detail_url))


@pytest.mark.django_db
def test_user_permissions_in_resource_endpoint(api_client, resource_in_unit, user):
    """
    Tests that resource endpoint returns a permissions dict with correct values.
    """
    api_client.force_authenticate(user=user)

    # normal user reservable True, expect is_admin False can_make_reservations True
    _check_permissions_dict(api_client, resource_in_unit, False, True)

    # normal user reservable False, expect is_admin False can_make_reservations False
    resource_in_unit.reservable = False
    resource_in_unit.save()
    _check_permissions_dict(api_client, resource_in_unit, False, False)

    # staff member reservable False, expect is_admin True can_make_reservations True
    user.is_staff = True
    user.save()
    api_client.force_authenticate(user=user)
    _check_permissions_dict(api_client, resource_in_unit, True, True)


@pytest.mark.django_db
def test_non_public_resource_visibility(api_client, resource_in_unit, user):
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

    # Authenticated as staff
    user.is_staff = True
    user.save()
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.data['count'] == 1

    url = reverse('resource-detail', kwargs={'pk': resource_in_unit.pk})
    response = api_client.get(url)
    assert response.status_code == 200


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
@pytest.mark.parametrize('endpoint', ['favorite', 'unfavorite'])
def test_resource_favorite_non_official(user_api_client, resource_in_unit, endpoint):
    url = '%s%s/' % (get_detail_url(resource_in_unit), endpoint)

    response = user_api_client.post(url)
    assert response.status_code == 403


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
def test_resource_unfavorite(staff_api_client, staff_user, resource_in_unit):
    url = '%sunfavorite/' % get_detail_url(resource_in_unit)

    response = staff_api_client.post(url)
    assert response.status_code == 304

    staff_user.favorite_resources.add(resource_in_unit)

    response = staff_api_client.post(url)
    assert response.status_code == 204
    assert resource_in_unit not in staff_user.favorite_resources.all()


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
    assert response.data['reservable_days_in_advance'] is None
    assert response.data['reservable_before'] is None

    test_unit.reservable_days_in_advance = 5
    test_unit.save()

    response = api_client.get(detail_url)
    assert response.status_code == 200

    # only the unit has days set, expect those on the resource
    assert response.data['reservable_days_in_advance'] == 5
    before = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=6)
    assert response.data['reservable_before'] == before

    resource_in_unit.reservable_days_in_advance = 10
    resource_in_unit.save()

    response = api_client.get(detail_url)
    assert response.status_code == 200

    # both the unit and the resource have days set, expect the resource's days to override the unit's days
    assert response.data['reservable_days_in_advance'] == 10
    before = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=11)
    assert response.data['reservable_before'] == before
