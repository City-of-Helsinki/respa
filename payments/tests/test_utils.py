from decimal import Decimal

import pytest

from payments.utils import price_as_sub_units, round_price


@pytest.fixture
def price_even():
    return Decimal('10.00')


@pytest.fixture
def price_round_up():
    return Decimal('9.995')


@pytest.fixture
def price_round_down():
    return Decimal('9.994')


def test_price_as_sub_units(price_even):
    """Test the price is converted to sub units"""
    even = price_as_sub_units(price_even)
    assert even == 1000


def test_round_price(price_even, price_round_up, price_round_down):
    """Test the price is round correctly"""
    even = round_price(price_even)
    up = round_price(price_round_up)
    down = round_price(price_round_down)
    assert even == Decimal('10.00')
    assert up == Decimal('10.00')
    assert down == Decimal('9.99')
