from copy import deepcopy

import pytest

from payments.models import Product, ARCHIVED_AT_NONE


@pytest.fixture(autouse=True)
def auto_use_django_db(db):
    pass


@pytest.fixture()
def product_1():
    return Product.objects.create(
        name_en='test product 1',
        code='1',
    )


@pytest.fixture()
def product_2():
    return Product.objects.create(
        name_en='test product 2',
        code='2',
    )


@pytest.fixture()
def product_1_v2(product_1):
    product_1_v2 = deepcopy(product_1)
    product_1_v2.name_en = 'test product 1 version 2'
    product_1_v2.save()
    product_1.refresh_from_db()
    return product_1_v2


def test_product_creation(product_1, product_2):
    assert product_1.product_id == 1
    assert product_2.product_id == 2
    assert Product.objects.count() == 2
    assert Product.objects.current().count() == 2


def test_product_update(product_1, product_1_v2):
    assert Product.objects.all().count() == 2
    assert Product.objects.current().count() == 1
    assert product_1.name_en == 'test product 1'
    assert product_1.archived_at != ARCHIVED_AT_NONE
    assert product_1_v2.name_en == 'test product 1 version 2'
    assert product_1_v2.archived_at == ARCHIVED_AT_NONE


def test_product_delete(product_1_v2, product_2):
    product_1_v2.delete()

    assert Product.objects.count() == 3
    assert set([p.id for p in Product.objects.current()]) == {product_2.id}
