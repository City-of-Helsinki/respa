import pytest
from django.urls import reverse

from resources.tests.utils import assert_response_objects, check_keys, check_only_safe_methods_allowed

LIST_URL = reverse('cateringprovider-list')


def get_detail_url(catering_provider):
    return reverse('cateringprovider-detail', kwargs={'pk': catering_provider.pk})


@pytest.mark.django_db
def test_catering_provider_endpoint_disallowed_methods(user_api_client, catering_provider):
    check_only_safe_methods_allowed(user_api_client, (LIST_URL, get_detail_url(catering_provider)))


@pytest.mark.parametrize('endpoint', (
    'list',
    'detail',
))
@pytest.mark.django_db
def test_catering_provider_endpoints_get(user_api_client, catering_provider, endpoint):
    url = LIST_URL if endpoint == 'list' else get_detail_url(catering_provider)

    response = user_api_client.get(url)
    assert response.status_code == 200
    if endpoint == 'list':
        assert len(response.data['results']) == 1
        data = response.data['results'][0]
    else:
        data = response.data

    expected_keys = {
        'id',
        'name',
        'price_list_url',
        'units',
    }
    check_keys(data, expected_keys)

    assert data['id']
    assert data['name'] == catering_provider.name
    assert data['price_list_url'] == {'fi': catering_provider.price_list_url_fi}
    assert set(data['units']) == set(catering_provider.units.values_list('id', flat=True))


@pytest.mark.django_db
def test_unit_filter(user_api_client, catering_provider, catering_provider2, test_unit2, test_unit3):
    response = user_api_client.get(LIST_URL)
    assert response.status_code == 200
    assert_response_objects(response, (catering_provider, catering_provider2))

    response = user_api_client.get(LIST_URL + '?unit=%s' % test_unit2.pk)
    assert response.status_code == 200
    assert_response_objects(response, catering_provider2)

    response = user_api_client.get(LIST_URL + '?unit=%s' % test_unit3.pk)
    assert response.status_code == 200
    assert len(response.data['results']) == 0
