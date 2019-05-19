# -*- coding: utf-8 -*-
import pytest

from resources.models import Equipment, ResourceGroup, ResourceEquipment
from django.urls import reverse

from .utils import assert_response_objects, check_only_safe_methods_allowed


@pytest.fixture
def list_url():
    return reverse('equipment-list')


@pytest.mark.django_db
@pytest.fixture
def detail_url(equipment):
    return reverse('equipment-detail', kwargs={'pk': equipment.pk})


def _check_keys_and_values(result):
    """
    Check that given dict represents equipment data in correct form.
    """
    assert len(result) == 4  # id, name, aliases, category
    assert result['id'] != ''
    assert result['name'] == {'fi': 'test equipment'}
    aliases = result['aliases']
    assert len(aliases) == 1
    assert aliases[0]['name'] == 'test equipment alias'
    assert aliases[0]['language'] == 'fi'
    category = result['category']
    assert category['name'] == {'fi': 'test equipment category'}
    assert category['id'] != ''


@pytest.mark.django_db
def test_disallowed_methods(all_user_types_api_client, list_url, detail_url):
    """
    Tests that only safe methods are allowed to equipment list and detail endpoints.
    """
    check_only_safe_methods_allowed(all_user_types_api_client, (list_url, detail_url))


@pytest.mark.django_db
def test_get_equipment_list(api_client, list_url, equipment, equipment_alias):
    """
    Tests that equipment list endpoint return equipment data in correct form.
    """
    response = api_client.get(list_url)
    results = response.data['results']
    assert len(results) == 1
    _check_keys_and_values(results[0])


@pytest.mark.django_db
def test_get_equipment_detail(api_client, detail_url, equipment, equipment_alias):
    """
    Tests that equipment detail endpoint returns equipment data in correct form.
    """
    response = api_client.get(detail_url)
    _check_keys_and_values(response.data)


@pytest.mark.django_db
def test_get_equipment_in_resource(api_client, resource_in_unit, resource_equipment):
    """
    Tests that combined resource equipment and equipment data is available via resource endpoint.

    Equipment aliases should not be included.
    """
    response = api_client.get(reverse('resource-detail', kwargs={'pk': resource_in_unit.pk}))
    equipments = response.data['equipment']
    assert len(equipments) == 1
    equipment = equipments[0]
    assert all(key in equipment for key in ('id', 'name', 'data', 'description'))
    assert 'aliases' not in equipment
    assert len(equipment['data']) == 1
    assert equipment['data']['test_key'] == 'test_value'
    assert equipment['description'] == {'fi': 'test resource equipment'}
    assert equipment['name'] == {'fi': 'test equipment'}


@pytest.mark.django_db
def test_resource_group_filter(api_client, equipment_category, resource_in_unit, resource_in_unit2, resource_in_unit3,
                               list_url):
    equipment_1 = Equipment.objects.create(name='test equipment 1', category=equipment_category)
    ResourceEquipment.objects.create(equipment=equipment_1, resource=resource_in_unit)

    equipment_2 = Equipment.objects.create(name='test equipment 2', category=equipment_category)
    ResourceEquipment.objects.create(equipment=equipment_2, resource=resource_in_unit2)

    equipment_3 = Equipment.objects.create(name='test equipment 3', category=equipment_category)
    ResourceEquipment.objects.create(equipment=equipment_3, resource=resource_in_unit3)

    equipment_4 = Equipment.objects.create(name='test equipment 4', category=equipment_category)
    ResourceEquipment.objects.create(equipment=equipment_4, resource=resource_in_unit)
    ResourceEquipment.objects.create(equipment=equipment_4, resource=resource_in_unit2)

    group_1 = ResourceGroup.objects.create(name='test group 1', identifier='test_group_1')
    resource_in_unit.groups.set([group_1])

    group_2 = ResourceGroup.objects.create(name='test group 2', identifier='test_group_2')
    resource_in_unit2.groups.set([group_1, group_2])

    group_3 = ResourceGroup.objects.create(name='test group 3', identifier='test_group_3')
    resource_in_unit3.groups.set([group_3])

    response = api_client.get(list_url)
    assert response.status_code == 200
    assert_response_objects(response, (equipment_1, equipment_2, equipment_3, equipment_4))

    response = api_client.get(list_url + '?' + 'resource_group=' + group_1.identifier)
    assert response.status_code == 200
    assert_response_objects(response, (equipment_1, equipment_2, equipment_4))

    response = api_client.get(list_url + '?' + 'resource_group=' + group_2.identifier)
    assert response.status_code == 200
    assert_response_objects(response, (equipment_2, equipment_4))

    response = api_client.get(list_url + '?' + 'resource_group=%s,%s' % (group_2.identifier, group_3.identifier))
    assert response.status_code == 200
    assert_response_objects(response, (equipment_2, equipment_3, equipment_4))

    response = api_client.get(list_url + '?' + 'resource_group=foobar')
    assert response.status_code == 200
    assert len(response.data['results']) == 0
