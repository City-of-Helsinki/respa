from decimal import Decimal

import pytest
from rest_framework.reverse import reverse

from ..factories import ProductFactory
from ..models import Product

LIST_URL = reverse('resource-list')

PRODUCT_FIELDS = {'id', 'type', 'name', 'description', 'tax_percentage', 'price', 'price_type'}


def get_detail_url(resource):
    return reverse('resource-detail', kwargs={'pk': resource.pk})


@pytest.fixture(autouse=True)
def auto_use_django_db(db):
    pass


@pytest.mark.parametrize('endpoint', ('list', 'detail'))
def test_get_resource_list_check_products(endpoint, user_api_client, resource_in_unit):
    # When using ProductFactory to create a product, it actually creates one
    # additional archived version of the same product, because factoryboy and
    # our same table versioned Products don't play together flawlessly. But
    # we can use that "feature" to our advantage here, as we can check that
    # those extra versions aren't returned by the resource API. We have an
    # assert here to make sure the "feature" isn't fixed.
    product = ProductFactory.create(
        tax_percentage=Decimal('24.00'),
        price=Decimal('10.00'),
        resources=[resource_in_unit],
    )
    assert Product.objects.count() == 2

    if endpoint == 'list':
        url = LIST_URL
    else:
        url = get_detail_url(resource_in_unit)
    response = user_api_client.get(url)

    assert response.status_code == 200

    if endpoint == 'list':
        products_data = response.data['results'][0]['products']
    else:
        products_data = response.data['products']
    assert len(products_data) == 1

    product_data = products_data[0]
    assert set(product_data.keys()) == PRODUCT_FIELDS
    assert product_data['id'] == product.product_id
    assert product_data['name'] == {'fi': product.name_fi}
    assert product_data['description'] == {'fi': product.description}
    assert product_data['price'] == '10.00'
    for field in ('type', 'tax_percentage', 'price_type'):
        assert product_data[field] == str(getattr(product, field))
