import pytest
from django.urls import reverse

from resources.tests.utils import assert_response_objects, check_keys, check_only_safe_methods_allowed

LIST_URL = reverse('cateringproduct-list')


def get_detail_url(catering_product):
    return reverse('cateringproduct-detail', kwargs={'pk': catering_product.pk})


@pytest.mark.django_db
def test_catering_product_endpoint_disallowed_methods(user_api_client, catering_product):
    check_only_safe_methods_allowed(user_api_client, (LIST_URL, get_detail_url(catering_product)))


@pytest.mark.parametrize('endpoint', (
    'list',
    'detail',
))
@pytest.mark.django_db
def test_catering_product_endpoints_get(user_api_client, catering_product, endpoint):
    url = LIST_URL if endpoint == 'list' else get_detail_url(catering_product)

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
        'category',
        'description',
    }
    check_keys(data, expected_keys)

    assert data['id']
    assert data['name'] == {'fi': catering_product.name_fi}


@pytest.mark.django_db
def test_provider_filter(user_api_client, catering_provider, catering_product, catering_product2):

    response = user_api_client.get(LIST_URL)
    assert response.status_code == 200
    assert_response_objects(response, (catering_product, catering_product2))

    response = user_api_client.get(LIST_URL + '?provider=%s' % catering_provider.pk)
    assert response.status_code == 200
    assert_response_objects(response, catering_product)

    response = user_api_client.get(LIST_URL + '?provider=87568957858789698798')
    assert response.status_code == 200
    assert len(response.data['results']) == 0


@pytest.mark.django_db
def test_category_filter(user_api_client, catering_product_category, catering_product,
                         catering_product2):

    response = user_api_client.get(LIST_URL)
    assert response.status_code == 200
    assert_response_objects(response, (catering_product, catering_product2))

    response = user_api_client.get(LIST_URL + '?category=%s' % catering_product_category.pk)
    assert response.status_code == 200
    assert_response_objects(response, catering_product)

    response = user_api_client.get(LIST_URL + '?category=87568957858789698798')
    assert response.status_code == 400
