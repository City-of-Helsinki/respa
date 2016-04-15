import pytest
from django.utils.crypto import get_random_string

from resources.models import Resource, ResourceType
from respa_exchange.models import ExchangeConfiguration


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
def exchange():
    return ExchangeConfiguration.objects.create(
        url="https://127.0.0.1:8000/%s.asmx" % get_random_string(),
        password=get_random_string(),
        username=get_random_string(),
    )
