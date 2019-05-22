from decimal import Decimal

import pytest


@pytest.fixture(autouse=True)
def auto_use_django_db(db):
    pass


def test_get_pretax_price_correct(order_with_products):
    """Test price calculation returns the correct combined taxfree sum for products

    Two hour reservation of two products with a price of 10 should equal 40"""
    pretax_price = order_with_products.get_pretax_price()
    assert pretax_price == Decimal('40.00')


def test_get_price_correct(order_with_products):
    """Test price calculation returns the correct combined sum for products

    Two hour reservation of two order lines with a price of 10, plus
    individual product tax of 24% should equal 49.60"""
    price = order_with_products.get_price()
    assert price == Decimal('49.60')
