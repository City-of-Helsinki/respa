from datetime import timedelta
from decimal import Decimal

import pytest

from payments.factories import OrderLineFactory
from payments.models import Product


@pytest.fixture(autouse=True)
def auto_use_django_db(db):
    pass


@pytest.fixture
def order_line_price(two_hour_reservation):
    return OrderLineFactory(
        quantity=1,
        product__price=Decimal('12.40'),
        product__tax_percentage=Decimal('24.00'),
        product__price_type=Product.PRICE_PER_PERIOD,
        product__price_period=timedelta(hours=1),
        order__reservation=two_hour_reservation
    )


def test_get_price_correct(order_line_price):
    """Test price calculation works correctly for prices with tax

    Two hour reservation of one product with a price of 12.40, plus
    individual product tax of 24% should equal 24.80"""
    price = order_line_price.get_price()
    assert price == Decimal('24.80')
