from datetime import timedelta

import pytest
from django.core import management
from django.utils.timezone import now

from resources.models import Reservation

from ..factories import OrderFactory
from ..models import Order, OrderLogEntry

PAYMENT_WAITING_MINUTES = 15
REQUESTED_PAYMENT_WAITING_HOURS = 24

COMMAND_NAME = 'expire_too_old_unpaid_orders'


def get_order_expired_time():
    return now() - (timedelta(minutes=PAYMENT_WAITING_MINUTES) + timedelta(seconds=10))


def get_order_not_expired_time():
    return now() - (timedelta(minutes=PAYMENT_WAITING_MINUTES) - timedelta(seconds=10))


@pytest.fixture(autouse=True)
def init(db, settings):
    settings.RESPA_PAYMENTS_PAYMENT_WAITING_TIME = PAYMENT_WAITING_MINUTES
    settings.RESPA_PAYMENTS_PAYMENT_REQUESTED_WAITING_TIME = REQUESTED_PAYMENT_WAITING_HOURS


def set_order_created_at(order, created_at):
    OrderLogEntry.objects.filter(id=order.log_entries.first().id).update(timestamp=created_at)


def test_orders_wont_get_expired_too_soon(two_hour_reservation, order_with_products):
    set_order_created_at(order_with_products, get_order_not_expired_time())

    management.call_command(COMMAND_NAME)

    assert two_hour_reservation.state == Reservation.WAITING_FOR_PAYMENT
    assert order_with_products.state == Order.WAITING


def test_orders_get_expired(two_hour_reservation, order_with_products):
    set_order_created_at(order_with_products, get_order_expired_time())

    management.call_command(COMMAND_NAME)

    two_hour_reservation.refresh_from_db()
    order_with_products.refresh_from_db()
    assert two_hour_reservation.state == Reservation.CANCELLED
    assert order_with_products.state == Order.EXPIRED


def test_requested_reservation_orders_get_expired(order_with_products):
    order_with_products.is_requested_order = True
    order_with_products.confirmed_by_staff_at = now() - timedelta(hours=REQUESTED_PAYMENT_WAITING_HOURS + 1)
    order_with_products.save()
    management.call_command(COMMAND_NAME)

    order_with_products.refresh_from_db()
    assert order_with_products.state == Order.EXPIRED
    assert order_with_products.reservation.state == Reservation.CANCELLED


@pytest.mark.parametrize('order_state', (Order.CANCELLED, Order.REJECTED, Order.CONFIRMED))
def test_other_than_waiting_order_wont_get_expired(two_hour_reservation, order_state):
    order = OrderFactory(reservation=two_hour_reservation, state=order_state)
    reservation_state = order.reservation.state
    set_order_created_at(order, get_order_expired_time())

    management.call_command(COMMAND_NAME)

    two_hour_reservation.refresh_from_db()
    order.refresh_from_db()
    assert two_hour_reservation.state == reservation_state
    assert order.state == order_state
