from datetime import timedelta
from random import randint

import factory
import factory.fuzzy
import factory.random

from resources.models import Reservation
from resources.models.utils import generate_id

from .models import ARCHIVED_AT_NONE, TAX_PERCENTAGES, Order, OrderLine, Product


class ProductFactory(factory.django.DjangoModelFactory):
    """Mock Product objects"""

    # Mandatory fields
    product_id = factory.Faker('uuid4')
    sku = factory.Faker('uuid4')
    type = factory.fuzzy.FuzzyChoice(Product.TYPE_CHOICES,
                                     getter=lambda c: c[0])
    price = factory.fuzzy.FuzzyDecimal(5.00, 100.00)
    price_type = factory.fuzzy.FuzzyChoice(Product.PRICE_TYPE_CHOICES,
                                           getter=lambda c: c[0])
    price_period = factory.lazy_attribute(
        lambda obj:
            timedelta(hours=factory.random.randgen.randrange(1, 10))
            if obj.price_type == Product.PRICE_PER_PERIOD
            else None
    )
    tax_percentage = factory.fuzzy.FuzzyChoice(TAX_PERCENTAGES)
    # created_at, defaults to now()
    archived_at = ARCHIVED_AT_NONE

    # Optional fields
    name = factory.Faker('catch_phrase')
    description = factory.Faker('text')
    max_quantity = factory.fuzzy.FuzzyInteger(5, 100)

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

    @factory.post_generation
    def reservation_state(obj, create, extracted, **kwargs):
        if extracted:
            state = extracted
        else:
            if obj.state == Order.CONFIRMED:
                state = Reservation.CONFIRMED
            elif obj.state in (Order.CANCELLED, Order.REJECTED, Order.EXPIRED):
                state = Reservation.CANCELLED
            else:
                state = Reservation.WAITING_FOR_PAYMENT
        Reservation.objects.filter(id=obj.reservation.id).update(state=state)
        obj.reservation.refresh_from_db()


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
