import pytest
from django.urls import reverse

list_url = reverse('incubating:resource-list')


def get_detail_url(reservation):
    return reverse('incubating:resource-detail', kwargs={'pk': reservation.pk})


@pytest.mark.django_db
def test_child_resources_pks_in_list(api_client, guide_resource):
    response = api_client.get(list_url)
    assert response.status_code == 200
    assert response.data['results'][0]['child_resources'][0] == guide_resource.id


@pytest.mark.django_db
def test_child_resources_nested_in_detail(api_client, resource_in_unit, guide_resource):
    response = api_client.get(get_detail_url(resource_in_unit))
    assert response.status_code == 200
    assert response.data['child_resources'][0]['id'] == guide_resource.id


@pytest.mark.django_db
def test_child_resources_not_present_on_top_level_in_list(api_client, resource_in_unit, guide_resource):
    response = api_client.get(list_url)
    assert response.status_code == 200
    results = response.data['results']
    assert len(results) == 1
    assert results[0]['id'] == resource_in_unit.id


@pytest.mark.django_db
def test_child_resources_have_detail(api_client, guide_resource):
    response = api_client.get(get_detail_url(guide_resource))
    assert response.status_code == 200
    assert response.data['id'] == guide_resource.id
