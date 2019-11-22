from unittest.mock import MagicMock, create_autospec, patch
from urllib.parse import urlencode

import pytest
from guardian.shortcuts import assign_perm
from rest_framework.reverse import reverse

from resources.enums import UnitAuthorizationLevel
from resources.models import Reservation
from resources.models.unit import UnitAuthorization
from resources.tests.conftest import resource_in_unit, user_api_client  # noqa
from resources.tests.test_reservation_api import day_and_period  # noqa

from ..factories import ProductFactory
from ..models import Order, Product
from ..providers.base import PaymentProvider
from .test_order_api import ORDER_LINE_FIELDS, PRODUCT_FIELDS

LIST_URL = reverse('reservation-list')

ORDER_FIELDS = {'id', 'state', 'price', 'order_lines'}


def get_detail_url(reservation):
    return reverse('reservation-detail', kwargs={'pk': reservation.pk})


def build_reservation_data(resource):
    return {
        'resource': resource.pk,
        'begin': '2115-04-04T11:00:00+02:00',
        'end': '2115-04-04T12:00:00+02:00'
    }


def build_order_data(product, quantity=None, product_2=None, quantity_2=None):
    data = {
        "order_lines": [
            {
                "product": product.product_id,
            }
        ],
        "return_url": "https://varauspalvelu.com/payment_return_url/",
    }

    if quantity:
        data['order_lines'][0]['quantity'] = quantity

    if product_2:
        order_line_data = {'product': product_2.product_id}
        if quantity_2:
            order_line_data['quantity'] = quantity_2
        data['order_lines'].append(order_line_data)

    return data


@pytest.fixture(autouse=True)
def auto_use_django_db(db):
    pass


@pytest.fixture
def product(resource_in_unit):
    return ProductFactory(resources=[resource_in_unit])


@pytest.fixture
def product_2(resource_in_unit):
    return ProductFactory(resources=[resource_in_unit])


@pytest.fixture(autouse=True)
def mock_provider():
    mocked_provider = create_autospec(PaymentProvider)
    mocked_provider.initiate_payment = MagicMock(return_value='https://mocked-payment-url.com')
    with patch('payments.api.reservation.get_payment_provider', return_value=mocked_provider):
        yield mocked_provider


@pytest.mark.parametrize('has_order, expected_state', (
    (False, Reservation.CONFIRMED),
    (True, Reservation.WAITING_FOR_PAYMENT),
))
def test_reservation_creation_state(user_api_client, resource_in_unit, has_order, expected_state):
    reservation_data = build_reservation_data(resource_in_unit)
    if has_order:
        product = ProductFactory(type=Product.RENT, resources=[resource_in_unit])
        reservation_data['order'] = build_order_data(product)

    response = user_api_client.post(LIST_URL, reservation_data)

    assert response.status_code == 201
    new_reservation = Reservation.objects.last()
    assert new_reservation.state == expected_state


@pytest.mark.parametrize('endpoint', ('list', 'detail'))
@pytest.mark.parametrize('include', (None, '', 'foo', ['foo', 'bar'], 'order_detail', ['foo', 'order_detail']))
def test_reservation_orders_field(user_api_client, order_with_products, endpoint, include):
    url = LIST_URL if endpoint == 'list' else get_detail_url(order_with_products.reservation)
    if include is not None:
        if not isinstance(include, list):
            include = list(include)
        query_string = urlencode([('include', i) for i in include])
        url += '?' + query_string

    response = user_api_client.get(url)
    assert response.status_code == 200

    reservation_data = response.data['results'][0] if endpoint == 'list' else response.data

    order_data = reservation_data['order']
    if include is not None and 'order_detail' in include:
        # order should be nested data
        assert set(order_data.keys()) == ORDER_FIELDS
        assert order_data['id'] == order_with_products.order_number
        for ol in order_data['order_lines']:
            assert set(ol.keys()) == ORDER_LINE_FIELDS
            assert set(ol['product']) == PRODUCT_FIELDS
    else:
        # order should be just ID
        assert order_data == order_with_products.order_number


@pytest.mark.parametrize('endpoint', ('list', 'detail'))
@pytest.mark.parametrize('request_user, expected', (
    (None, False),
    ('owner', True),
    ('other', False),
    ('other_with_perm', True),
))
def test_reservation_order_field_visibility(api_client, order_with_products, user2, request_user, endpoint, expected):
    url = LIST_URL if endpoint == 'list' else get_detail_url(order_with_products.reservation)

    if request_user == 'owner':
        api_client.force_authenticate(user=order_with_products.reservation.user)
    elif request_user == 'other':
        api_client.force_authenticate(user=user2)
    elif request_user == 'other_with_perm':
        assign_perm('unit:can_view_reservation_product_orders', user2, order_with_products.reservation.resource.unit)
        api_client.force_authenticate(user=user2)

    response = api_client.get(url)
    assert response.status_code == 200

    reservation_data = response.data['results'][0] if endpoint == 'list' else response.data
    assert ('order' in reservation_data) is expected


def test_reservation_in_state_waiting_for_payment_cannot_be_modified_or_deleted(user_api_client, order_with_products):
    reservation = order_with_products.reservation
    response = user_api_client.put(get_detail_url(reservation), data=build_reservation_data(reservation.resource))
    assert response.status_code == 403

    response = user_api_client.delete(get_detail_url(reservation))
    assert response.status_code == 403


@pytest.mark.parametrize('has_perm', (False, True))
def test_reservation_that_has_order_cannot_be_modified_without_permission(user_api_client, order_with_products, user,
                                                                          has_perm):
    order_with_products.set_state(Order.CONFIRMED)
    if has_perm:
        assign_perm('unit:can_modify_paid_reservations', user, order_with_products.reservation.resource.unit)

    data = build_reservation_data(order_with_products.reservation.resource)
    response = user_api_client.put(get_detail_url(order_with_products.reservation), data=data)
    assert response.status_code == 200 if has_perm else 403

    response = user_api_client.delete(get_detail_url(order_with_products.reservation))
    assert response.status_code == 204 if has_perm else 403


def test_order_post(user_api_client, resource_in_unit, product, product_2, mock_provider):
    reservation_data = build_reservation_data(resource_in_unit)
    reservation_data['order'] = build_order_data(product=product, product_2=product_2, quantity_2=5)

    response = user_api_client.post(LIST_URL, reservation_data)

    assert response.status_code == 201, response.data
    mock_provider.initiate_payment.assert_called()

    # check response fields
    order_create_response_fields = ORDER_FIELDS.copy() | {'payment_url'}
    order_data = response.data['order']
    assert set(order_data.keys()) == order_create_response_fields
    assert order_data['payment_url'].startswith('https://mocked-payment-url.com')

    # check created object
    new_order = Order.objects.last()
    assert new_order.reservation == Reservation.objects.last()

    # check order lines
    order_lines = new_order.order_lines.all()
    assert order_lines.count() == 2
    assert order_lines[0].product == product
    assert order_lines[0].quantity == 1
    assert order_lines[1].product == product_2
    assert order_lines[1].quantity == 5


def test_order_product_must_match_resource(user_api_client, product, resource_in_unit, resource_in_unit2):
    product_with_another_resource = ProductFactory(resources=[resource_in_unit2])
    data = build_reservation_data(resource_in_unit)
    data['order'] = build_order_data(product=product, product_2=product_with_another_resource)

    response = user_api_client.post(LIST_URL, data)

    assert response.status_code == 400
    assert 'product' in response.data['order']['order_lines'][1]


def test_order_line_products_are_unique(user_api_client, resource_in_unit, product):
    """Test order validator enforces that order lines cannot contain duplicates of the same product"""
    reservation_data = build_reservation_data(resource_in_unit)
    reservation_data['order'] = build_order_data(product, quantity=2, product_2=product, quantity_2=2)
    response = user_api_client.post(LIST_URL, reservation_data)

    assert response.status_code == 400


@pytest.mark.parametrize('quantity, expected_status', (
    (1, 201),
    (2, 201),
    (3, 400),
))
def test_order_line_product_quantity_limitation(user_api_client, resource_in_unit, quantity, expected_status):
    """Test order validator order line quantity is within product max quantity limitation"""
    reservation_data = build_reservation_data(resource_in_unit)
    product_with_quantity = ProductFactory(resources=[resource_in_unit], max_quantity=2)
    order_data = build_order_data(product=product_with_quantity, quantity=quantity)
    reservation_data['order'] = order_data

    response = user_api_client.post(LIST_URL, reservation_data)

    assert response.status_code == expected_status, response.data


@pytest.mark.parametrize('has_rent', (True, False))
def test_rent_product_makes_order_required_(user_api_client, resource_in_unit, has_rent):
    reservation_data = build_reservation_data(resource_in_unit)
    if has_rent:
        ProductFactory(type=Product.RENT, resources=[resource_in_unit])

    response = user_api_client.post(LIST_URL, reservation_data)

    if has_rent:
        assert response.status_code == 400
        assert 'order' in response.data
    else:
        assert response.status_code == 201


def test_order_cannot_be_modified(user_api_client, order_with_products, user):
    order_with_products.set_state(Order.CONFIRMED)
    assert order_with_products.reservation.state == Reservation.CONFIRMED
    new_product = ProductFactory(resources=[order_with_products.reservation.resource])
    reservation_data = build_reservation_data(order_with_products.reservation.resource)
    reservation_data['order'] = {
        'order_lines': [{
            'product': new_product.product_id,
            'quantity': 777
        }],
        'return_url': 'https://foo'
    }
    assign_perm('unit:can_modify_paid_reservations', user, order_with_products.reservation.resource.unit)

    response = user_api_client.put(get_detail_url(order_with_products.reservation), reservation_data)

    assert response.status_code == 200, response.data
    order_with_products.refresh_from_db()
    assert order_with_products.order_lines.first().product != new_product
    assert order_with_products.order_lines.first().quantity != 777
    assert order_with_products.order_lines.count() > 1


def test_extra_product_doesnt_make_order_required(user_api_client, resource_in_unit):
    reservation_data = build_reservation_data(resource_in_unit)
    ProductFactory(type=Product.EXTRA, resources=[resource_in_unit])

    response = user_api_client.post(LIST_URL, reservation_data)

    assert response.status_code == 201


def test_order_must_include_rent_if_one_exists(user_api_client, resource_in_unit):
    reservation_data = build_reservation_data(resource_in_unit)
    ProductFactory(type=Product.RENT, resources=[resource_in_unit])
    extra = ProductFactory(type=Product.EXTRA, resources=[resource_in_unit])
    reservation_data['order'] = build_order_data(product=extra)

    response = user_api_client.post(LIST_URL, reservation_data)
    assert response.status_code == 400


def test_unit_admin_and_unit_manager_may_bypass_payment(user_api_client, resource_in_unit, user):
    reservation_data = build_reservation_data(resource_in_unit)
    ProductFactory(type=Product.RENT, resources=[resource_in_unit])

    # Order required for normal user
    response = user_api_client.post(LIST_URL, reservation_data)
    assert response.status_code == 400
    assert 'order' in response.data

    # Order not required for admin user
    UnitAuthorization.objects.create(subject=resource_in_unit.unit, level=UnitAuthorizationLevel.admin, authorized=user)
    response = user_api_client.post(LIST_URL, reservation_data)
    assert response.status_code == 201
    new_reservation = Reservation.objects.last()
    assert new_reservation.state == Reservation.CONFIRMED
    UnitAuthorization.objects.all().delete()
    Reservation.objects.all().delete()

    # Order not required for manager user
    UnitAuthorization.objects.create(subject=resource_in_unit.unit, level=UnitAuthorizationLevel.manager, authorized=user)
    response = user_api_client.post(LIST_URL, reservation_data)
    assert response.status_code == 201
    new_reservation = Reservation.objects.last()
    assert new_reservation.state == Reservation.CONFIRMED