import pytest
from guardian.shortcuts import assign_perm
from rest_framework.reverse import reverse

from resources.models import Reservation
from resources.tests.conftest import resource_in_unit, user_api_client  # noqa
from resources.tests.test_reservation_api import day_and_period  # noqa

from ..factories import ProductFactory
from ..models import Product
from ..tests.test_order_api import ORDER_RESPONSE_FIELDS

LIST_URL = reverse('reservation-list')

ORDER_FIELDS = ORDER_RESPONSE_FIELDS - {'reservation', 'payment_url'}


def get_detail_url(reservation):
    return reverse('reservation-detail', kwargs={'pk': reservation.pk})


@pytest.mark.parametrize('has_rent_product, expected_state', (
    (False, Reservation.CONFIRMED),
    (True, Reservation.WAITING_FOR_PAYMENT),
))
@pytest.mark.django_db
def test_reservation_creation_state(user_api_client, resource_in_unit, has_rent_product, expected_state):
    if has_rent_product:
        ProductFactory(type=Product.RENT, resources=[resource_in_unit])
    data = {
        'resource': resource_in_unit.pk,
        'begin': '2115-04-04T11:00:00+02:00',
        'end': '2115-04-04T12:00:00+02:00'
    }

    response = user_api_client.post(LIST_URL, data)
    assert response.status_code == 201, response.data
    new_reservation = Reservation.objects.last()
    assert new_reservation.state == expected_state


@pytest.mark.parametrize('endpoint', ('list', 'detail'))
@pytest.mark.parametrize('include', (None, '', 'foo', 'foo,bar', 'orders', 'foo,orders'))
@pytest.mark.django_db
def test_reservation_orders_field(user_api_client, order_with_products, endpoint, include):
    url = LIST_URL if endpoint == 'list' else get_detail_url(order_with_products.reservation)
    if include is not None:
        url += '?include={}'.format(include)

    response = user_api_client.get(url)
    assert response.status_code == 200

    reservation_data = response.data['results'][0] if endpoint == 'list' else response.data

    order_data = reservation_data['orders'][0]
    if include is not None and 'orders' in include:
        # orders should be nested data
        assert set(order_data.keys()) == ORDER_FIELDS
        assert order_data['id'] == order_with_products.id
    else:
        # orders should be just IDs
        assert order_data == order_with_products.id


@pytest.mark.parametrize('endpoint', ('list', 'detail'))
@pytest.mark.parametrize('request_user, expected', (
    (None, False),
    ('owner', True),
    ('other', False),
    ('other_with_perm', True),
))
@pytest.mark.django_db
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
    assert ('orders' in reservation_data) is expected
