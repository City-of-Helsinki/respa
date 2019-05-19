# -*- coding: utf-8 -*-
import pytest

from resources.models import ResourceGroup, ResourceType
from django.urls import reverse

from .utils import assert_response_objects, check_only_safe_methods_allowed


@pytest.fixture
def list_url():
    return reverse('resourcetype-list')


@pytest.mark.django_db
@pytest.fixture
def detail_url(space_resource):
    return reverse('resourcetype-detail', kwargs={'pk': space_resource.pk})


@pytest.mark.django_db
def test_disallowed_methods(all_user_types_api_client, list_url, detail_url):
    """
    Tests that only safe methods are allowed to resource type list and detail endpoints.
    """
    check_only_safe_methods_allowed(all_user_types_api_client, (list_url, detail_url))


@pytest.mark.django_db
def test_resource_group_filter(api_client, resource_in_unit, resource_in_unit2, resource_in_unit3,
                               space_resource_type, list_url):
    type_1 = ResourceType.objects.create(name='test resource type 1')
    resource_in_unit.type = type_1
    resource_in_unit.save()

    type_2 = ResourceType.objects.create(name='test resource type 2')
    resource_in_unit2.type = type_2
    resource_in_unit2.save()

    type_3 = ResourceType.objects.create(name='test resource type 3')
    resource_in_unit3.type = type_3
    resource_in_unit3.save()

    space_resource_type.delete()

    group_1 = ResourceGroup.objects.create(name='test group 1', identifier='test_group_1')
    resource_in_unit.groups.set([group_1])

    group_2 = ResourceGroup.objects.create(name='test group 2', identifier='test_group_2')
    resource_in_unit2.groups.set([group_1, group_2])

    group_3 = ResourceGroup.objects.create(name='test group 3', identifier='test_group_3')
    resource_in_unit3.groups.set([group_3])

    response = api_client.get(list_url)
    assert response.status_code == 200
    assert_response_objects(response, (type_1, type_2, type_3))

    response = api_client.get(list_url + '?' + 'resource_group=' + group_1.identifier)
    assert response.status_code == 200
    assert_response_objects(response, (type_1, type_2))

    response = api_client.get(list_url + '?' + 'resource_group=' + group_2.identifier)
    assert response.status_code == 200
    assert_response_objects(response, type_2)

    response = api_client.get(list_url + '?' + 'resource_group=%s,%s' % (group_2.identifier, group_3.identifier))
    assert response.status_code == 200
    assert_response_objects(response, (type_2, type_3))

    response = api_client.get(list_url + '?' + 'resource_group=foobar')
    assert response.status_code == 200
    assert len(response.data['results']) == 0
