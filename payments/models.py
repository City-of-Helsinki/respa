import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models, transaction, IntegrityError
from django.db.models import Max
from django.utils.timezone import now, utc
from django.utils.translation import ugettext_lazy as _

from resources.models import Reservation, Resource

from .utils import round_price

# The best way for representing non existing archived_at would be using None for it,
# but that would not work with the unique_together constraint, which brings many
# benefits, so we use this sentinel value instead of None.
ARCHIVED_AT_NONE = datetime(9999, 12, 31, tzinfo=utc)


class ProductQuerySet(models.QuerySet):
    def current(self):
        return self.filter(archived_at=ARCHIVED_AT_NONE)


class Product(models.Model):
    RENT = 'rent'
    TYPE_CHOICES = (
        (RENT, _('rent')),
    )

    PER_HOUR = 'per_hour'
    PRICE_TYPE_CHOICES = (
        (PER_HOUR, _('per hour')),
    )

    created_at = models.DateTimeField(verbose_name=_('created at'), auto_now_add=True)

    # This ID is common to all versions of the same product, and is the one
    # used as ID in the API.
    product_id = models.PositiveIntegerField(verbose_name=_('product ID'), editable=False, db_index=True)

    # archived_at determines when this version of the product has been either (soft)
    # deleted or replaced by a newer version. Value ARCHIVED_AT_NONE means this is the
    # current version in use.
    archived_at = models.DateTimeField(
        verbose_name=_('archived_at'), db_index=True, editable=False, default=ARCHIVED_AT_NONE
    )

    type = models.CharField(max_length=32, verbose_name=_('type'), choices=TYPE_CHOICES, default=RENT)
    sku = models.CharField(max_length=255, verbose_name=_('SKU'))
    name = models.CharField(max_length=100, verbose_name=_('name'), blank=True)
    description = models.TextField(verbose_name=_('description'), blank=True)

    pretax_price = models.DecimalField(
        verbose_name=_('pretax price'), max_digits=14, decimal_places=2, default='0.00',
        validators=[MinValueValidator(0)]
    )
    tax_percentage = models.DecimalField(
        verbose_name=_('tax percentage'), max_digits=5, decimal_places=2, default='24.00',
        choices=(('0.00', '0.00'), ('10.00', '10.00'), ('14.00', '14.00'), ('24.00', '24.00'))
    )
    price_type = models.CharField(
        max_length=32, verbose_name=_('price type'), choices=PRICE_TYPE_CHOICES, default=PER_HOUR
    )

    resources = models.ManyToManyField(Resource, verbose_name=_('resource'), related_name='products', blank=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = _('product')
        verbose_name_plural = _('products')
        ordering = ('id',)
        unique_together = ('archived_at', 'product_id')

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.id:
            self._save_existing(*args, **kwargs)
        else:
            self._save_new(*args, **kwargs)

    def delete(self, *args, **kwargs):
        Product.objects.filter(id=self.id).update(archived_at=now())

    def _save_existing(self, *args, **kwargs):
        """
        Save an already existing product.

        Marks the previous version archived and creates a new Product instance.
        """
        assert self.id
        Product.objects.filter(id=self.id).update(archived_at=now())
        self.id = None
        super().save(*args, **kwargs)

    def _save_new(self, *args, **kwargs):
        """
        Save a new product.

        We need to generate a product_id for this new product, which is carried out by
        optimistically trying out next free product_id value(s). Because there is a
        chance of a race, we try several product_id values until a free one is found.
        """
        assert not self.id
        current_product_id_max = Product.objects.aggregate(Max('product_id'))['product_id__max'] or 0
        self.product_id = current_product_id_max + 1
        for _i in range(11):  # 11 determined using the Stetson-Harrison method
            with transaction.atomic():
                try:
                    super().save(*args, **kwargs)
                    break
                except IntegrityError:  # there was a race and someone beat us
                    self.product_id += 1
                    transaction.set_rollback(True)  # needed because of the IntegrityError
                    continue
        else:
            raise Exception('Cannot obtain a new product ID for product {}.'.format(self))

    def get_price(self):
        return round_price(self.pretax_price * (1 + Decimal(self.tax_percentage) / 100))

    def get_pretax_price_for_time_range(self, begin: datetime, end: datetime, rounded: bool = True) -> Decimal:
        assert begin < end

        if self.price_type == Product.PER_HOUR:
            price = self.pretax_price * Decimal((end - begin) / timedelta(hours=1))
        else:
            raise NotImplementedError('Cannot calculate price, unknown price type "{}".'.format(self.price_type))

        if rounded:
            price = round_price(price)

        return price

    def get_price_for_time_range(self, begin: datetime, end: datetime, rounded: bool = True) -> Decimal:
        pretax_price = self.get_pretax_price_for_time_range(begin, end, rounded=False)
        price = pretax_price * (1 + Decimal(self.tax_percentage) / 100)

        if rounded:
            price = round_price(price)

        return price

    def get_pretax_price_for_reservation(self, reservation: Reservation, rounded: bool = True) -> Decimal:
        return self.get_pretax_price_for_time_range(reservation.begin, reservation.end, rounded)

    def get_price_for_reservation(self, reservation: Reservation, rounded: bool = True) -> Decimal:
        return self.get_price_for_time_range(reservation.begin, reservation.end, rounded)


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

    def get_pretax_price(self) -> Decimal:
        return sum(order_line.get_pretax_price() for order_line in self.order_lines.all())

    def get_price(self) -> Decimal:
        return sum(order_line.get_price() for order_line in self.order_lines.all())


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

    def get_pretax_price(self) -> Decimal:
        return self.product.get_pretax_price_for_reservation(self.order.reservation) * self.quantity

    def get_price(self) -> Decimal:
        return self.product.get_price_for_reservation(self.order.reservation) * self.quantity
