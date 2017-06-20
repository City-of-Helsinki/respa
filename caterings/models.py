from django.core.validators import MinValueValidator
from django.contrib.gis.db import models
from django.contrib.gis.db.models import Q
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import pgettext_lazy

import reversion

from resources.models import Reservation, Resource, Unit


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(verbose_name=_('time of creation'), editable=False, auto_now_add=True)
    modified_at = models.DateTimeField(verbose_name=_('time of modification'), editable=False, auto_now=True)

    class Meta:
        abstract = True


class CateringProvider(TimeStampedModel):
    name = models.CharField(max_length=100, verbose_name=_('Name'))
    price_list_url = models.URLField(verbose_name=_('Price list URL'), blank=True)
    units = models.ManyToManyField(Unit, verbose_name=_('Units'), related_name='catering_providers', blank=True)

    class Meta:
        verbose_name = _('Catering provider')
        verbose_name_plural = _('Catering providers')

    def __str__(self):
        return self.name


class CateringProductCategory(TimeStampedModel):
    name = models.CharField(max_length=100, verbose_name=_('Catering product category'))
    provider = models.ForeignKey(
        CateringProvider, verbose_name=_('Catering provider'), related_name='catering_product_categories',
        on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = _('Catering product category')
        verbose_name_plural = _('Catering product categories')

    def __str__(self):
        return '%s (%s)' % (self.name, self.provider)


class CateringProduct(TimeStampedModel):
    name = models.CharField(max_length=100, verbose_name=_('Name'))
    category = models.ForeignKey(
        CateringProductCategory, verbose_name=pgettext_lazy('catering', 'Category'), related_name='products',
        on_delete=models.CASCADE
    )
    description = models.TextField(verbose_name=_('Description'), blank=True)

    class Meta:
        verbose_name = _('Catering product')
        verbose_name_plural = _('Catering products')

    def __str__(self):
        return '%s (%s)' % (self.name, self.category.provider)


class CateringOrderQuerySet(models.QuerySet):
    def can_view(self, user):
        if not user.is_authenticated():
            return self.none()

        allowed_resources = Resource.objects.with_perm('can_view_reservation_catering_orders', user)
        allowed_reservations = Reservation.objects.filter(Q(resource__in=allowed_resources) | Q(user=user))

        return self.filter(reservation__in=allowed_reservations)


@reversion.register(follow=('order_lines',))
class CateringOrder(TimeStampedModel):
    reservation = models.ForeignKey(
        Reservation, verbose_name=_('Reservation'), related_name='catering_orders', on_delete=models.CASCADE
    )
    invoicing_data = models.TextField(verbose_name=_('Invoicing data'))
    message = models.TextField(verbose_name=_('Message'), blank=True)
    serving_time = models.TimeField(verbose_name=_('Serving time'), blank=True, null=True)

    objects = CateringOrderQuerySet.as_manager()

    class Meta:
        verbose_name = _('Catering order')
        verbose_name_plural = _('Catering orders')

    def __str__(self):
        return 'catering order for %s' % self.reservation


@reversion.register()
class CateringOrderLine(models.Model):
    product = models.ForeignKey(
        CateringProduct, verbose_name=_('Product'), related_name='catering_order_line',
        on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(verbose_name=_('Quantity'), validators=(MinValueValidator(1),), default=1)
    order = models.ForeignKey(
        CateringOrder, verbose_name=_('Order'), related_name='order_lines', on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = _('Catering order line')
        verbose_name_plural = _('Catering order lines')

    def __str__(self):
        return '%s %s %s' % (self.quantity, self.product, self.order)
