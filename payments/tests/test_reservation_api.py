import pytest
from guardian.shortcuts import assign_perm
from rest_framework.reverse import reverse

from resources.models import Reservation
from resources.tests.conftest import resource_in_unit, user_api_client  # noqa
from resources.tests.test_reservation_api import day_and_period  # noqa

from ..factories import ProductFactory
from ..models import Order, Product
from ..tests.test_order_api import ORDER_RESPONSE_FIELDS

LIST_URL = reverse('reservation-list')

ORDER_FIELDS = ORDER_RESPONSE_FIELDS - {'reservation', 'payment_url'}


def get_detail_url(reservation):
    return reverse('reservation-detail', kwargs={'pk': reservation.pk})


def get_data(resource):
    return {
        'resource': resource.pk,
        'begin': '2115-04-04T11:00:00+02:00',
        'end': '2115-04-04T12:00:00+02:00'
    }


@pytest.fixture(autouse=True)
def auto_use_django_db(db):
    pass


@pytest.mark.parametrize('has_rent_product, expected_state', (
    (False, Reservation.CONFIRMED),
    (True, Reservation.WAITING_FOR_PAYMENT),
))
def test_reservation_creation_state(user_api_client, resource_in_unit, has_rent_product, expected_state):
    if has_rent_product:
        ProductFactory(type=Product.RENT, resources=[resource_in_unit])

    response = user_api_client.post(LIST_URL, get_data(resource_in_unit))
    assert response.status_code == 201, response.data
    new_reservation = Reservation.objects.last()
    assert new_reservation.state == expected_state


@pytest.mark.parametrize('endpoint', ('list', 'detail'))
@pytest.mark.parametrize('include', (None, '', 'foo', 'foo,bar', 'order', 'foo,order'))
def test_reservation_orders_field(user_api_client, order_with_products, endpoint, include):
    url = LIST_URL if endpoint == 'list' else get_detail_url(order_with_products.reservation)
    if include is not None:
        url += '?include={}'.format(include)

    response = user_api_client.get(url)
    assert response.status_code == 200

    reservation_data = response.data['results'][0] if endpoint == 'list' else response.data

    order_data = reservation_data['order']
    if include is not None and 'order' in include:
        # order should be nested data
        assert set(order_data.keys()) == ORDER_FIELDS
        assert order_data['id'] == order_with_products.order_number
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
def test_reservation_orders_field_visibility(api_client, order_with_products, user2, request_user, endpoint, expected):
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


def test_reservation_in_state_waiting_for_payment_cannot_be_modified_or_deleted(user_api_client, two_hour_reservation):
    response = user_api_client.put(get_detail_url(two_hour_reservation), data=get_data(two_hour_reservation.resource))
    assert response.status_code == 403

    response = user_api_client.delete(get_detail_url(two_hour_reservation))
    assert response.status_code == 403


@pytest.mark.parametrize('has_perm', (False, True))
def test_reservation_that_has_order_cannot_be_modified_without_permission(user_api_client, order_with_products, user,
                                                                          has_perm):
    order_with_products.set_state(Order.CONFIRMED)
    if has_perm:
        assign_perm('unit:can_modify_paid_reservations', user, order_with_products.reservation.resource.unit)

    response = user_api_client.put(
        get_detail_url(order_with_products.reservation), data=get_data(order_with_products.reservation.resource)
    )
    assert response.status_code == 200 if has_perm else 403

    response = user_api_client.delete(get_detail_url(order_with_products.reservation))
    assert response.status_code == 204 if has_perm else 403
