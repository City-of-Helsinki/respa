import pytest
from django.urls import reverse

from ..views.resources import ResourceListView

url = reverse('respa_admin:index')


@pytest.mark.django_db
def test_order_by_name(rf, general_admin, resource_in_unit, resource_in_unit2):
    resource_in_unit.name = 'aaaaa'
    resource_in_unit.save()
    resource_in_unit2.name = 'bbbbb'
    resource_in_unit2.save()

    request = rf.get(url + '?order_by=name')
    request.user = general_admin
    response = ResourceListView.as_view()(request)
    resources = response.context_data.get('resources')
    assert resources[0] == resource_in_unit

    request = rf.get(url + '?order_by=-name')
    request.user = general_admin
    response = ResourceListView.as_view()(request)
    resources = response.context_data.get('resources')
    assert resources[0] == resource_in_unit2


@pytest.mark.django_db
def test_order_by_reservable(rf, general_admin, resource_in_unit, resource_in_unit2):
    resource_in_unit2.reservable = False
    resource_in_unit2.save()

    request = rf.get(url + '?order_by=reservable')
    request.user = general_admin
    response = ResourceListView.as_view()(request)
    resources = response.context_data.get('resources')
    assert resources[0] == resource_in_unit2

    request = rf.get(url + '?order_by=-reservable')
    request.user = general_admin
    response = ResourceListView.as_view()(request)
    resources = response.context_data.get('resources')
    assert resources[0] == resource_in_unit


@pytest.mark.django_db
def test_order_by_public(rf, general_admin, resource_in_unit, resource_in_unit2):
    resource_in_unit2.public = False
    resource_in_unit2.save()

    request = rf.get(url + '?order_by=public')
    request.user = general_admin
    response = ResourceListView.as_view()(request)
    resources = response.context_data.get('resources')
    assert resources[0] == resource_in_unit2

    request = rf.get(url + '?order_by=-public')
    request.user = general_admin
    response = ResourceListView.as_view()(request)
    resources = response.context_data.get('resources')
    assert resources[0] == resource_in_unit
