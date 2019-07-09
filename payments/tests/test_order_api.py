import pytest
from guardian.shortcuts import assign_perm
from rest_framework.reverse import reverse

from ..factories import ProductFactory
from ..models import Order

LIST_URL = reverse('order-list')
CHECK_PRICE_URL = reverse('order-check-price')

ORDER_RESPONSE_FIELDS = {
    'reservation', 'id', 'price', 'state', 'order_lines'
}


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


def test_order_get_list(user_api_client, order_with_products):
    response = user_api_client.get(LIST_URL)

    assert response.status_code == 200
    results = response.data['results']
    assert len(results) == 1
    assert set(results[0].keys()) == ORDER_RESPONSE_FIELDS


def test_order_get_detail(user_api_client, order_with_products):
    response = user_api_client.get(get_detail_url(order_with_products))

    assert response.status_code == 200
    assert set(response.data.keys()) == ORDER_RESPONSE_FIELDS


def test_order_put_forbidden(user_api_client, order_with_products):
    response = user_api_client.put(get_detail_url(order_with_products))
    assert response.status_code == 405


def test_order_patch_forbidden(user_api_client, order_with_products):
    response = user_api_client.patch(get_detail_url(order_with_products))
    assert response.status_code == 405


def test_order_post_forbidden(user_api_client, order_with_products):
    response = user_api_client.post(get_detail_url(order_with_products))
    assert response.status_code == 405


def test_order_view_permissions(api_client, user2, order_with_products):
    # unauthenticated user
    response = api_client.get(LIST_URL)
    assert response.status_code == 200
    assert not response.data['results']

    # not own reservation
    api_client.force_authenticate(user=user2)
    response = api_client.get(LIST_URL)
    assert response.status_code == 200
    assert not response.data['results']

    # not own reservation but having the view permission
    assign_perm('unit:can_view_reservation_product_orders', user2, order_with_products.reservation.resource.unit)
    response = api_client.get(LIST_URL)
    assert response.status_code == 200
    assert len(response.data['results']) == 1


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
    assert set(response.data.keys()) == {'order_lines', 'price', 'begin', 'end'}
    # Check order count didn't change
    assert order_count_before == Order.objects.count()