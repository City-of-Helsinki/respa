from datetime import timedelta

import pytest

from django.core import management
from django.utils.timezone import now

from payments.models import OrderLogEntry, Order
from resources.models import Reservation
from resources.models.reservation import ORDER_WAITING_TIME

PAYMENT_WAITING_MINUTES = 15


def get_reservation_expired_time():
    return now() - (ORDER_WAITING_TIME + timedelta(seconds=10))


def get_reservation_not_expired_time():
    return now() - (ORDER_WAITING_TIME - timedelta(seconds=10))


def get_order_expired_time():
    return now() - (timedelta(minutes=PAYMENT_WAITING_MINUTES) + timedelta(seconds=10))


def get_order_not_expired_time():
    return now() - (timedelta(minutes=PAYMENT_WAITING_MINUTES) - timedelta(seconds=10))


@pytest.fixture(autouse=True)
def init(db, settings):
    settings.RESPA_PAYMENTS_PAYMENT_WAITING_TIME = PAYMENT_WAITING_MINUTES


def set_reservation_created_at(reservation, created_at):
    Reservation.objects.filter(id=reservation.id).update(created_at=created_at)


def set_order_created_at(order, created_at):
    OrderLogEntry.objects.filter(id=order.log_entries.first().id).update(timestamp=created_at)


def test_reservations_and_orders_wont_get_expired_too_soon(two_hour_reservation, order_with_products):
    set_reservation_created_at(two_hour_reservation, get_reservation_not_expired_time())
    set_order_created_at(order_with_products, get_order_not_expired_time())

    management.call_command('update_expired_orders_and_reservations')

    assert two_hour_reservation.state == Reservation.WAITING_FOR_PAYMENT
    assert order_with_products.state == Order.WAITING


def test_waiting_for_payment_reservations_get_expired(two_hour_reservation):
    set_reservation_created_at(two_hour_reservation, get_order_expired_time())

    management.call_command('update_expired_orders_and_reservations')

    two_hour_reservation.refresh_from_db()
    assert two_hour_reservation.state == Reservation.CANCELLED


@pytest.mark.parametrize('state', (Reservation.REQUESTED, Reservation.DENIED, Reservation.CONFIRMED))
def test_other_than_waiting_for_payment_reservations_wont_get_expired(two_hour_reservation, state):
    Reservation.objects.filter(id=two_hour_reservation.id).update(state=state)
    set_reservation_created_at(two_hour_reservation, get_reservation_expired_time())

    management.call_command('update_expired_orders_and_reservations')

    two_hour_reservation.refresh_from_db()
    assert two_hour_reservation.state == state


@pytest.mark.django_db
def test_reservations_with_order_wont_get_expired_on_their_own(two_hour_reservation, order_with_products):
    set_reservation_created_at(two_hour_reservation, get_reservation_expired_time())

    management.call_command('update_expired_orders_and_reservations')

    two_hour_reservation.refresh_from_db()
    assert two_hour_reservation.state == Reservation.WAITING_FOR_PAYMENT


@pytest.mark.django_db
def test_orders_get_expired(two_hour_reservation, order_with_products):
    set_order_created_at(order_with_products, get_order_expired_time())

    management.call_command('update_expired_orders_and_reservations')

    two_hour_reservation.refresh_from_db()
    order_with_products.refresh_from_db()
    assert two_hour_reservation.state == Reservation.CANCELLED
    assert order_with_products.state == Order.EXPIRED
