import pytest
from guardian.shortcuts import assign_perm
from rest_framework.reverse import reverse

from ..factories import ProductFactory
from ..models import Order

CHECK_PRICE_URL = reverse('order-check-price')


PRICE_ENDPOINT_ORDER_FIELDS = {
    'order_lines', 'price', 'begin', 'end'
}

ORDER_LINE_FIELDS = {
    'product', 'quantity', 'price', 'unit_price'
}

PRODUCT_FIELDS = {
    'id', 'type', 'name', 'description', 'price', 'max_quantity'
}

PRICE_FIELDS = {'type'}


def get_detail_url(order):
    return reverse('order-detail', kwargs={'order_number': order.order_number})


@pytest.fixture(autouse=True)
def auto_use_django_db(db):
    pass


@pytest.fixture
def product(resource_in_unit):
    return ProductFactory(resources=[resource_in_unit])


@pytest.fixture
def product_2(resource_in_unit):
    return ProductFactory(resources=[resource_in_unit])


def test_order_price_check_success(user_api_client, product, two_hour_reservation):
    """Test the endpoint returns price calculations for given product without persisting anything"""

    order_count_before = Order.objects.count()

    price_check_data = {
        "order_lines": [
            {
                "product": product.product_id,
            }
        ],
        "begin": str(two_hour_reservation.begin),
        "end": str(two_hour_reservation.end)
    }

    response = user_api_client.post(CHECK_PRICE_URL, price_check_data)
    assert response.status_code == 200
    assert len(response.data['order_lines']) == 1
    assert set(response.data.keys()) == PRICE_ENDPOINT_ORDER_FIELDS
    for ol in response.data['order_lines']:
        assert set(ol.keys()) == ORDER_LINE_FIELDS
        assert set(ol['product']) == PRODUCT_FIELDS
        assert all(f in ol['product']['price'] for f in PRICE_FIELDS)

    # Check order count didn't change
    assert order_count_before == Order.objects.count()
