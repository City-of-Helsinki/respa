
from random import randint

import factory
import factory.fuzzy

from resources.models.utils import generate_id

from .models import ARCHIVED_AT_NONE, TAX_PERCENTAGES, Order, OrderLine, Product


class ProductFactory(factory.django.DjangoModelFactory):
    """Mock Product objects"""

    # Mandatory fields
    product_id = factory.Faker('uuid4')
    sku = factory.Faker('uuid4')
    type = factory.fuzzy.FuzzyChoice(Product.TYPE_CHOICES,
                                     getter=lambda c: c[0])
    pretax_price = factory.fuzzy.FuzzyDecimal(5.00, 100.00)
    price_type = factory.fuzzy.FuzzyChoice(Product.PRICE_TYPE_CHOICES,
                                           getter=lambda c: c[0])
    tax_percentage = factory.fuzzy.FuzzyChoice(TAX_PERCENTAGES)
    # created_at, defaults to now()
    archived_at = ARCHIVED_AT_NONE

    # Optional fields
    name = factory.Faker('catch_phrase')
    description = factory.Faker('text')

    @factory.post_generation
    def resources(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            self.resources.set(extracted)

    class Meta:
        model = Product


class OrderFactory(factory.django.DjangoModelFactory):
    """Mock Order objects

    Reservation fixture has to be given as a parameter
    TODO Provide Reservations / Resources through SubFactory
    """

    # Mandatory fields
    state = factory.fuzzy.FuzzyChoice(Order.STATE_CHOICES,
                                      getter=lambda c: c[0])
    order_number = generate_id()

    # Mandatory FKs
    reservation = None

    class Meta:
        model = Order


class OrderWithOrderLinesFactory(OrderFactory):
    """Mock Order objects, with order lines"""

    @factory.post_generation
    def order_lines(obj, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for n in range(extracted):
                OrderLineFactory(order=obj)
        else:
            line_count = randint(1, 10)
            for n in range(line_count):
                OrderLineFactory(order=obj)


class OrderLineFactory(factory.django.DjangoModelFactory):
    """Mock OrderLine objects"""
    quantity = factory.fuzzy.FuzzyInteger(1, 10)
    order = factory.SubFactory(OrderFactory)
    product = factory.SubFactory(ProductFactory)

    class Meta:
        model = OrderLine
