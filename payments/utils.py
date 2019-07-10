from decimal import ROUND_HALF_UP, Decimal
from functools import wraps


def price_as_sub_units(price: Decimal) -> int:
    return int(round_price(price) * 100)


def round_price(price: Decimal) -> Decimal:
    return price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def rounded(func):
    """
    Decorator for conditionally rounding function result

    By default the result is rounded to two decimal places, but the rounding
    can be turned off by giving parameter "rounded=False" when calling the
    function.
    """
    @wraps(func)
    def wrapped(*args, **kwargs):
        rounded = kwargs.pop('rounded', True)
        value = func(*args, **kwargs)
        if rounded:
            value = round_price(value)
        return value
    return wrapped


def convert_pretax_to_aftertax(pretax_price: Decimal, tax_percentage: Decimal) -> Decimal:
    return pretax_price * (1 + tax_percentage / 100)


def convert_aftertax_to_pretax(aftertax_price: Decimal, tax_percentage: Decimal) -> Decimal:
    return aftertax_price / (1 + tax_percentage / 100)


def get_tax_amount_from_aftertax(aftertax_price: Decimal, tax_percentage: Decimal) -> Decimal:
    return convert_aftertax_to_pretax(aftertax_price, tax_percentage) * (tax_percentage / 100)


def get_tax_amount_from_pretax(pretax_price: Decimal, tax_percentage: Decimal) -> Decimal:
    return pretax_price * (tax_percentage / 100)
