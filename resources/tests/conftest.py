# -*- coding: utf-8 -*-
import pytest
from rest_framework.test import APIClient, APIRequestFactory

from resources.models import Resource, ResourceType, Unit


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
