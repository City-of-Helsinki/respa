from decimal import Decimal

import pytest

from resources.models import Reservation

from ..exceptions import OrderStateTransitionError
from ..factories import OrderFactory
from ..models import Order


@pytest.fixture(autouse=True)
def auto_use_django_db(db):
    pass


def test_get_price_correct(order_with_products):
    """Test price calculation returns the correct combined sum for products

    Two hour reservation of two order lines with a price of 10, where one product
    has an hourly rate and one is with a fixed price, plus individual product
    tax of 24% should equal 37.20"""
    price = order_with_products.get_price()
    assert price == Decimal('37.20')


@pytest.mark.parametrize('order_state, expected_reservation_state', (
    (Order.CONFIRMED, Reservation.CONFIRMED),
    (Order.REJECTED, Reservation.CANCELLED),
    (Order.EXPIRED, Reservation.CANCELLED),
    (Order.CANCELLED, Reservation.CANCELLED),
))
def test_set_state_sets_reservation_state(two_hour_reservation, order_state, expected_reservation_state):
    old_order_state = Order.CONFIRMED if order_state == Order.CANCELLED else Order.WAITING
    order = OrderFactory(reservation=two_hour_reservation, state=old_order_state)

    order.set_state(order_state)

    two_hour_reservation.refresh_from_db()
    assert two_hour_reservation.state == expected_reservation_state


@pytest.mark.parametrize('state, new_state', (
    (Order.REJECTED, Order.CONFIRMED),
    (Order.REJECTED, Order.EXPIRED),
    (Order.REJECTED, Order.CANCELLED),
    (Order.CONFIRMED, Order.REJECTED),
    (Order.CONFIRMED, Order.EXPIRED),
    (Order.EXPIRED, Order.REJECTED),
    (Order.EXPIRED, Order.CONFIRMED),
    (Order.EXPIRED, Order.CANCELLED),
    (Order.CANCELLED, Order.REJECTED),
    (Order.CANCELLED, Order.CONFIRMED),
    (Order.CANCELLED, Order.EXPIRED),
    (Order.WAITING, Order.CANCELLED),
))
def test_set_state_denied_transitions(two_hour_reservation, state, new_state):
    order = OrderFactory(reservation=two_hour_reservation, state=state)
    with pytest.raises(OrderStateTransitionError):
        order.set_state(new_state)


@pytest.mark.parametrize('state, new_state', (
    (Order.WAITING, Order.CONFIRMED),
    (Order.WAITING, Order.EXPIRED),
    (Order.WAITING, Order.REJECTED),
    (Order.CONFIRMED, Order.CANCELLED),
))
def test_set_state_allowed_transitions(two_hour_reservation, state, new_state):
    order = OrderFactory(reservation=two_hour_reservation, state=state)
    order.set_state(new_state)
    assert order.state == new_state
