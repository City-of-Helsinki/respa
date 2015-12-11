# -*- coding: utf-8 -*-
import pytest

from resources.models import Equipment, EquipmentAlias, ResourceEquipment
from django.core.urlresolvers import reverse

from .utils import check_only_safe_methods_allowed


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