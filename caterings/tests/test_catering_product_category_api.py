import pytest
from django.urls import reverse

from resources.tests.utils import assert_response_objects, check_keys, check_only_safe_methods_allowed

LIST_URL = reverse('cateringproductcategory-list')


def get_detail_url(catering_product_category):
    return reverse('cateringproductcategory-detail', kwargs={'pk': catering_product_category.pk})


@pytest.mark.django_db
def test_catering_provider_endpoint_disallowed_methods(user_api_client, catering_product_category):
    check_only_safe_methods_allowed(user_api_client, (LIST_URL, get_detail_url(catering_product_category)))


@pytest.mark.parametrize('endpoint', (
    'list',
    'detail',
))
@pytest.mark.django_db
def test_catering_product_category_endpoints_get(user_api_client, catering_product_category, endpoint):
    url = LIST_URL if endpoint == 'list' else get_detail_url(catering_product_category)

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
        'products',
        'provider',
    }
    check_keys(data, expected_keys)

    assert data['id']
    assert data['name'] == {'fi': catering_product_category.name_fi}
    assert data['provider'] == catering_product_category.provider.pk


@pytest.mark.django_db
def test_provider_filter(user_api_client, catering_provider, catering_product_category,
                         catering_product_category2):

    response = user_api_client.get(LIST_URL)
    assert response.status_code == 200
    assert_response_objects(response, (catering_product_category, catering_product_category2))

    response = user_api_client.get(LIST_URL + '?provider=%s' % catering_provider.pk)
    assert response.status_code == 200
    assert_response_objects(response, catering_product_category)

    response = user_api_client.get(LIST_URL + '?provider=not_a_provider')
    assert response.status_code == 400
