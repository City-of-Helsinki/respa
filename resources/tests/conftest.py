# -*- coding: utf-8 -*-
import pytest
import datetime
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APIRequestFactory

from resources.models import Resource, ResourceType, Unit
from resources.models import Equipment, EquipmentAlias, ResourceEquipment, EquipmentCategory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def api_rf():
    return APIRequestFactory()


@pytest.mark.django_db
@pytest.fixture
def space_resource_type():
    return ResourceType.objects.get_or_create(id="test_space", name="test_space", main_type="space")[0]


@pytest.mark.django_db
@pytest.fixture
def space_resource(space_resource_type):
    return Resource.objects.create(type=space_resource_type, authentication="none", name="resource")


@pytest.mark.django_db
@pytest.fixture
def test_unit():
    return Unit.objects.create(name="unit")


@pytest.mark.django_db
@pytest.fixture
def resource_in_unit(space_resource_type, test_unit):
    return Resource.objects.create(
        type=space_resource_type,
        authentication="none",
        name="resource in unit",
        unit=test_unit,
        max_reservations_per_user=1,
        max_period=datetime.timedelta(hours=2),
        reservable=True,
    )


@pytest.mark.django_db
@pytest.fixture
def equipment_category():
    return EquipmentCategory.objects.create(
        name='test equipment category'
    )


@pytest.mark.django_db
@pytest.fixture
def equipment(equipment_category):
    equipment = Equipment.objects.create(name='test equipment', category=equipment_category)
    return equipment


@pytest.mark.django_db
@pytest.fixture
def equipment_alias(equipment):
    equipment_alias = EquipmentAlias.objects.create(name='test equipment alias', language='fi', equipment=equipment)
    return equipment_alias


@pytest.mark.django_db
@pytest.fixture
def resource_equipment(resource_in_unit, equipment):
    data = {'test_key': 'test_value'}
    resource_equipment = ResourceEquipment.objects.create(
        equipment=equipment,
        resource=resource_in_unit,
        data=data,
        description='test resource equipment',
    )
    return resource_equipment


@pytest.mark.django_db
@pytest.fixture
def user():
    return get_user_model().objects.create(
        username='test_user',
        first_name='Cem',
        last_name='Kaner',
        email='cem@kaner.com'
    )


@pytest.mark.django_db
@pytest.fixture
def user2():
    return get_user_model().objects.create(
        username='test_user2',
        first_name='Brendan',
        last_name='Neutra',
        email='brendan@neutra.com'
    )