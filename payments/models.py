import uuid
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.core.validators import MaxValueValidator
from django.db import models
from django.utils.translation import ugettext_lazy as _

from resources.models import Reservation, Resource


class Product(models.Model):
    RENT = 'rent'
    TYPE_CHOICES = (
        (RENT, _('rent')),
    )

    PER_HOUR = 'per_hour'
    PRICE_TYPE_CHOICES = (
        (PER_HOUR, _('per hour')),
    )

    type = models.CharField(max_length=32, verbose_name=_('type'), choices=TYPE_CHOICES, default=RENT)
    code = models.CharField(max_length=255, verbose_name=_('code'))
    name = models.CharField(max_length=100, verbose_name=_('name'), blank=True)
    description = models.TextField(verbose_name=_('description'), blank=True)

    pretax_price = models.DecimalField(verbose_name=_('pretax price'), max_digits=14, decimal_places=2, default='0.00')
    tax_percentage = models.PositiveSmallIntegerField(
        verbose_name=_('tax percentage'), default=24, validators=[MaxValueValidator(100)]
    )
    price_type = models.CharField(
        max_length=32, verbose_name=_('price type'), choices=PRICE_TYPE_CHOICES, default=PER_HOUR
    )

    resources = models.ManyToManyField(Resource, verbose_name=_('resource'), related_name='products', blank=True)

    class Meta:
        verbose_name = _('product')
        verbose_name_plural = _('products')
        ordering = ('id',)

    def __str__(self):
        return self.name

    def get_pretax_price_for_reservation(self, reservation: Reservation, rounded: bool = True) -> Decimal:
        if self.price_type == Product.PER_HOUR:
            reservation_duration = reservation.end - reservation.begin
            pretax_price = self.pretax_price * Decimal(reservation_duration / timedelta(hours=1))
            if rounded:
                pretax_price = pretax_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            return pretax_price
        else:
            raise NotImplementedError('Cannot calculate price, unknown price type "{}".'.format(self.price_type))

    def get_price_for_reservation(self, reservation: Reservation, rounded: bool = True) -> Decimal:
        pretax_price = self.get_pretax_price_for_reservation(reservation, rounded=False)
        price = pretax_price * (1 + Decimal(self.tax_percentage) / 100)
        if rounded:
            price = price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        return price


class Order(models.Model):
    WAITING = 'waiting'
    CONFIRMED = 'confirmed'
    REJECTED = 'rejected'

    STATUS_CHOICES = (
        (WAITING, _('waiting')),
        (CONFIRMED, _('confirmed')),
        (REJECTED, _('rejected')),
    )

    status = models.CharField(max_length=32, verbose_name=_('status'), choices=STATUS_CHOICES, default=WAITING)
    order_number = models.CharField(max_length=64, verbose_name=_('order number'), unique=True, default=uuid.uuid4)
    reservation = models.OneToOneField(
        Reservation, verbose_name=_('reservation'), related_name='order', on_delete=models.PROTECT
    )

    class Meta:
        verbose_name = _('order')
        verbose_name_plural = _('orders')
        ordering = ('id',)

    def __str__(self):
        return '{} {}'.format(self.order_number, self.reservation)


class OrderLine(models.Model):
    order = models.ForeignKey(Order, verbose_name=_('order'), related_name='order_lines', on_delete=models.CASCADE)
    product = models.ForeignKey(
        Product, verbose_name=_('product'), related_name='order_lines', on_delete=models.PROTECT
    )

    quantity = models.PositiveIntegerField(verbose_name=_('quantity'), default=1)

    class Meta:
        verbose_name = _('order line')
        verbose_name_plural = _('order lines')
        ordering = ('id',)

    def __str__(self):
        return str(self.product)
