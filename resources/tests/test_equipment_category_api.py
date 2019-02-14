# -*- coding: utf-8 -*-
import pytest

from resources.models import Equipment, ResourceEquipment, EquipmentCategory
from django.urls import reverse

from .utils import check_disallowed_methods, UNSAFE_METHODS

@pytest.fixture
def list_url():
    return reverse('equipmentcategory-list')


@pytest.mark.django_db
@pytest.fixture
def detail_url(equipment_category):
    return reverse('equipmentcategory-detail', kwargs={'pk': equipment_category.pk})


def _check_keys_and_values(result):
    """
    Check that given dict represents equipment data in correct form.
    """
    assert len(result) == 3  # id, name, equipments
    assert result['id'] != ''
    assert result['name'] == {'fi': 'test equipment category'}
    equipments = result['equipment']
    assert len(equipments) == 1
    equipment = equipments[0]
    assert len(equipment) == 2
    assert equipment['name'] == {'fi': 'test equipment'}
    assert equipment['id'] != ''


@pytest.mark.django_db
def test_disallowed_methods(all_user_types_api_client, list_url, detail_url):
    """
    Tests that only safe methods are allowed to equipment list and detail endpoints.
    """
    check_disallowed_methods(all_user_types_api_client, (list_url, detail_url), UNSAFE_METHODS)


@pytest.mark.django_db
def test_get_equipment_category_list(api_client, list_url, equipment):
    """
    Tests that equipment category list endpoint returns equipment category data in correct form.
    """
    response = api_client.get(list_url)
    results = response.data['results']
    assert len(results) == 1
    _check_keys_and_values(results[0])


@pytest.mark.django_db
def test_get_equipment_category_list(api_client, detail_url, equipment):
    """
    Tests that equipment category detail endpoint returns equipment category data in correct form.
    """
    response = api_client.get(detail_url)
    _check_keys_and_values(response.data)
