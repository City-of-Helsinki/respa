import pytest

from payments.factories import OrderFactory

from ..models import Order, OrderLogEntry


@pytest.fixture(autouse=True)
def auto_use_django_db(db):
    pass


def test_order_log_entry_creation(order_with_products):
    order_with_products.create_log_entry(message='everything is lost')

    assert OrderLogEntry.objects.count() == 2  # there is already one from the order's creation
    order_log_entry = OrderLogEntry.objects.last()
    assert order_log_entry.order == order_with_products
    assert order_log_entry.timestamp
    assert not order_log_entry.state_change
    assert order_log_entry.message == 'everything is lost'


def test_order_log_entry_created_on_order_creation(order_with_products):
    order_log_entry = OrderLogEntry.objects.last()
    assert order_log_entry.order == order_with_products
    assert order_log_entry.state_change == Order.WAITING


@pytest.mark.parametrize('new_state', (Order.REJECTED, Order.CONFIRMED, Order.EXPIRED))
def test_order_log_entry_created_on_order_set_state(order_with_products, new_state):
    order_with_products.set_state(new_state)

    assert OrderLogEntry.objects.count() == 2
    order_log_entry = OrderLogEntry.objects.last()
    assert order_log_entry.state_change == new_state


def test_order_log_entry_not_created_on_order_set_state_when_state_stays_same(two_hour_reservation):
    order = OrderFactory(reservation=two_hour_reservation, state=Order.WAITING)
    assert OrderLogEntry.objects.count() == 1

    order.set_state(Order.WAITING)

    assert OrderLogEntry.objects.count() == 1
