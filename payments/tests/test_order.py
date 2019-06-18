from decimal import Decimal

import pytest

from resources.models import Reservation

from ..factories import OrderFactory
from ..models import Order


@pytest.fixture(autouse=True)
def auto_use_django_db(db):
    pass


def test_get_pretax_price_correct(order_with_products):
    """Test price calculation returns the correct combined taxfree sum for products

    Two hour reservation of two products with a price of 10, where one product
    has an hourly rate and one is with a fixed price, should equal 30"""
    pretax_price = order_with_products.get_pretax_price()
    assert pretax_price == Decimal('30.00')


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
    order = OrderFactory(reservation=two_hour_reservation, state=Order.WAITING)

    order.set_state(order_state)

    two_hour_reservation.refresh_from_db()
    assert two_hour_reservation.state == expected_reservation_state
