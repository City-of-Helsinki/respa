import pytest

from resources.tests.conftest import *
from resources.tests.test_reservation_api import reservation, reservation2, reservation3

from caterings.models import (
    CateringProduct, CateringProductCategory, CateringProvider, CateringOrder, CateringOrderLine
)


@pytest.fixture
def catering_provider(test_unit):
    provider = CateringProvider.objects.create(
        name='Kaikkein Kovin Catering Oy',
        price_list_url_fi='www.kaikkeinkovincatering.biz/hinnasto/',
    )
    provider.units.set([test_unit])
    return provider


@pytest.fixture
def catering_provider2(test_unit, test_unit2):
    provider = CateringProvider.objects.create(
        name='Lähes Yhtä Kova Catering Ab',
        price_list_url_fi='www.lahesyhtakovacatering.ninja/hinnat/',
    )
    provider.units.set([test_unit, test_unit2])
    return provider


@pytest.fixture
def catering_product_category(catering_provider):
    return CateringProductCategory.objects.create(
        name_fi='Kahvittelutuotteet',
        provider=catering_provider,
    )


@pytest.fixture
def catering_product_category2(catering_provider2):
    return CateringProductCategory.objects.create(
        name_fi='Keitot',
        provider=catering_provider2,
    )


@pytest.fixture
def catering_product(catering_product_category):
    return CateringProduct.objects.create(
        name_fi='Kahvi',
        category=catering_product_category,
    )


@pytest.fixture
def catering_product2(catering_product_category2):
    return CateringProduct.objects.create(
        name_fi='Hernekeitto',
        category=catering_product_category2,
    )


@pytest.fixture
def catering_product3(catering_product_category2):
    return CateringProduct.objects.create(
        name_fi='Kalakeitto',
        category=catering_product_category2,
    )


@pytest.fixture
def catering_order(catering_product, reservation, user):
    order = CateringOrder.objects.create(
        reservation=reservation,
        invoicing_data='777-777',
        message='lots of salt please',
        serving_time=datetime.time(12, 00, 00),
        provider=catering_product.category.provider
    )
    order_line = CateringOrderLine.objects.create(
        product=catering_product,
        quantity=1,
        order=order,
    )
    return order


@pytest.fixture
def catering_order2(catering_product2, reservation2):
    order = CateringOrder.objects.create(
        reservation=reservation2,
        invoicing_data='123456',
        message='NO SUGAR!',
        provider=catering_product2.category.provider
    )
    order_line = CateringOrderLine.objects.create(
        product=catering_product2,
        quantity=777,
        order=order,
    )
    return order


@pytest.fixture
def catering_order3(catering_product3, reservation3):
    order = CateringOrder.objects.create(
        reservation=reservation3,
        invoicing_data='xyz',
        provider=catering_product3.category.provider
    )
    order_line = CateringOrderLine.objects.create(
        product=catering_product3,
        order=order,
    )
    return order
