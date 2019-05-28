from copy import deepcopy

import pytest

from resources.tests.conftest import resource_in_unit  # noqa

from ..models import ARCHIVED_AT_NONE, Product


@pytest.fixture(autouse=True)
def auto_use_django_db(db):
    pass


@pytest.fixture()
def product_1(resource_in_unit):
    product = Product.objects.create(
        name_en='test product 1',
        sku='1',
    )
    product.resources.set([resource_in_unit])
    return product


@pytest.fixture()
def product_2():
    return Product.objects.create(
        name_en='test product 2',
        sku='2',
    )


@pytest.fixture()
def product_1_v2(product_1):
    product_1_v2 = deepcopy(product_1)
    product_1_v2.name_en = 'test product 1 version 2'
    product_1_v2.save()
    product_1.refresh_from_db()
    return product_1_v2


def test_product_creation(product_1, product_2, resource_in_unit):
    assert product_1.product_id != product_2.product_id
    assert Product.objects.count() == 2
    assert Product.objects.current().count() == 2
    assert set(product_1.resources.all()) == {resource_in_unit}


def test_product_update(product_1, product_1_v2, resource_in_unit):
    assert Product.objects.all().count() == 2
    assert Product.objects.current().count() == 1

    assert product_1.name_en == 'test product 1'
    assert product_1.archived_at != ARCHIVED_AT_NONE
    assert set(product_1.resources.all()) == {resource_in_unit}

    assert product_1_v2.name_en == 'test product 1 version 2'
    assert product_1_v2.archived_at == ARCHIVED_AT_NONE
    assert set(product_1_v2.resources.all()) == {resource_in_unit}


def test_product_delete(product_1_v2, product_2):
    product_1_v2.delete()

    assert Product.objects.count() == 3
    assert set([p.id for p in Product.objects.current()]) == {product_2.id}
