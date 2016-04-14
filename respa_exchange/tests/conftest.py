import pytest
from resources.models import ResourceType, Resource


# Fixtures snarfed from Respa.


@pytest.mark.django_db
@pytest.fixture
def space_resource_type():
    return ResourceType.objects.get_or_create(id="test_space", name="test_space", main_type="space")[0]


@pytest.mark.django_db
@pytest.fixture
def space_resource(space_resource_type):
    return Resource.objects.create(type=space_resource_type, authentication="none", name="resource")
