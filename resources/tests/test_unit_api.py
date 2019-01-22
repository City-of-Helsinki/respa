# -*- coding: utf-8 -*-
import datetime
import pytest

from django.urls import reverse
from django.utils import timezone
from freezegun import freeze_time

from resources.models import Resource, ResourceGroup
from .utils import assert_response_objects, check_only_safe_methods_allowed


@pytest.fixture
def list_url():
    return reverse('unit-list')


@pytest.mark.django_db
@pytest.fixture
def detail_url(test_unit):
    return reverse('unit-detail', kwargs={'pk': test_unit.pk})


@pytest.mark.django_db
def test_disallowed_methods(all_user_types_api_client, list_url, detail_url):
    """
    Tests that only safe methods are allowed to unit list and detail endpoints.
    """
    check_only_safe_methods_allowed(all_user_types_api_client, (list_url, detail_url))


@freeze_time('2016-10-25')
@pytest.mark.django_db
def test_reservable_in_advance_fields(api_client, test_unit, detail_url):
    response = api_client.get(detail_url)
    assert response.status_code == 200

    assert response.data['reservable_max_days_in_advance'] is None
    assert response.data['reservable_before'] is None

    test_unit.reservable_max_days_in_advance = 5
    test_unit.save()

    response = api_client.get(detail_url)
    assert response.status_code == 200

    assert response.data['reservable_max_days_in_advance'] == 5
    before = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=6)
    assert response.data['reservable_before'] == before


@pytest.mark.django_db
def test_resource_group_filter(api_client, test_unit, test_unit2, test_unit3, resource_in_unit, resource_in_unit2,
                               resource_in_unit3, list_url):
    # test_unit has 2 resources, test_unit3 none
    resource_in_unit3.unit = test_unit
    resource_in_unit3.save()

    group_1 = ResourceGroup.objects.create(name='test group 1', identifier='test_group_1')
    resource_in_unit.groups.set([group_1])
    resource_in_unit3.groups.set([group_1])

    group_2 = ResourceGroup.objects.create(name='test group 2', identifier='test_group_2')
    resource_in_unit2.groups.set([group_1, group_2])

    response = api_client.get(list_url)
    assert response.status_code == 200
    assert_response_objects(response, (test_unit, test_unit2, test_unit3))

    response = api_client.get(list_url + '?' + 'resource_group=' + group_1.identifier)
    assert response.status_code == 200
    assert_response_objects(response, (test_unit, test_unit2))

    response = api_client.get(list_url + '?' + 'resource_group=' + group_2.identifier)
    assert response.status_code == 200
    assert_response_objects(response, test_unit2)

    response = api_client.get(list_url + '?' + 'resource_group=%s,%s' % (group_1.identifier, group_2.identifier))
    assert response.status_code == 200
    assert_response_objects(response, (test_unit, test_unit2))

    response = api_client.get(list_url + '?' + 'resource_group=foobar')
    assert response.status_code == 200
    assert len(response.data['results']) == 0


@pytest.mark.django_db
def test_unit_has_resource_filter(api_client, test_unit,
                               resource_in_unit2, list_url):

    response = api_client.get(list_url + '?' + 'unit_has_resource=True')
    assert response.status_code == 200
    assert_response_objects(response, (resource_in_unit2.unit))

    response = api_client.get(list_url + '?' + 'unit_has_resource=False')
    assert response.status_code == 200
    assert_response_objects(response, (test_unit))