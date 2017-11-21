import pytest
from django.utils.crypto import get_random_string

from resources.models import Unit, Resource, ResourceType
from respa_exchange.models import ExchangeConfiguration


@pytest.mark.django_db
@pytest.fixture
def space_resource_type():
    """
    A ResourceType denoting a space
    """
    return ResourceType.objects.get_or_create(id="test_space", name="test_space", main_type="space")[0]


@pytest.mark.django_db
@pytest.fixture
def space_resource(space_resource_type):
    """
    An arbitrary space resource
    """
    unit = Unit.objects.create(name='unit 1')
    return Resource.objects.create(
        unit=unit, type=space_resource_type, authentication="none", name="resource"
    )


@pytest.mark.django_db
@pytest.fixture
def exchange():
    """
    An Exchange configuration for testing
    """
    return ExchangeConfiguration.objects.create(
        url="https://127.0.0.1:8000/%s.asmx" % get_random_string(),
        password=get_random_string(),
        username=get_random_string(),
    )
