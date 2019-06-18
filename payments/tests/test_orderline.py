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
        product__pretax_price=Decimal('10.00'),
        product__tax_percentage=Decimal('24.00'),
        product__price_type=Product.PRICE_PER_HOUR,
        order__reservation=two_hour_reservation
    )


def test_get_pretax_price_correct(order_line_price):
    """Test price calculation works correctly for prices without tax

    Two hour reservation of one product with a price of 10 should equal 40"""
    pretax_price = order_line_price.get_pretax_price()
    assert pretax_price == Decimal('20.00')


def test_get_price_correct(order_line_price):
    """Test price calculation works correctly for prices with tax

    Two hour reservation of one product with a price of 10, plus
    individual product tax of 24% should equal 24.80"""
    price = order_line_price.get_price()
    assert price == Decimal('24.80')
