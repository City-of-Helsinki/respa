
import factory
import factory.fuzzy

from random import randint

from .models import Product, TAX_PERCENTAGES, ARCHIVED_AT_NONE, Order, OrderLine
from resources.models.utils import generate_id


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

    # Optional FKs
    # resources

    class Meta:
        model = Product


class OrderFactory(factory.django.DjangoModelFactory):
    """Mock Order objects

    Reservation fixture has to be given as a parameter
    TODO Provide Reservations / Resources through SubFactory
    """

    # Mandatory fields
    payer_first_name = factory.Faker('first_name')
    payer_last_name = factory.Faker('last_name')
    payer_email_address = factory.Faker('email')
    payer_address_street = factory.Faker('street_address')
    payer_address_zip = factory.Faker('postcode')
    payer_address_city = factory.Faker('city')
    status = factory.fuzzy.FuzzyChoice(Order.STATUS_CHOICES,
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
