import logging

from django.core.validators import MinValueValidator
from django.contrib.gis.db import models
from django.contrib.gis.db.models import Q
from django.utils import formats, translation
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import pgettext_lazy

import reversion

from notifications.models import NotificationType, NotificationTemplateException, render_notification_template
from resources.models import Reservation, Resource, Unit
from resources.models.utils import DEFAULT_LANG, send_respa_mail

logger = logging.getLogger(__name__)


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(verbose_name=_('time of creation'), editable=False, auto_now_add=True)
    modified_at = models.DateTimeField(verbose_name=_('time of modification'), editable=False, auto_now=True)

    class Meta:
        abstract = True


class CateringProvider(TimeStampedModel):
    name = models.CharField(max_length=100, verbose_name=_('Name'))
    price_list_url = models.URLField(verbose_name=_('Price list URL'), blank=True)
    units = models.ManyToManyField(Unit, verbose_name=_('Units'), related_name='catering_providers', blank=True)
    notification_email = models.EmailField(verbose_name=_('Notification email'), blank=True)

    class Meta:
        verbose_name = _('Catering provider')
        verbose_name_plural = _('Catering providers')
        ordering = ('id',)

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
        ordering = ('provider', 'name')

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
        ordering = ('name',)

    def __str__(self):
        return '%s (%s)' % (self.name, self.category.provider)


class CateringOrderQuerySet(models.QuerySet):
    def can_view(self, user):
        if not user.is_authenticated:
            return self.none()

        allowed_resources = Resource.objects.with_perm('can_view_reservation_catering_orders', user)
        allowed_reservations = Reservation.objects.filter(Q(resource__in=allowed_resources) | Q(user=user))

        return self.filter(reservation__in=allowed_reservations)


@reversion.register(follow=('order_lines',))
class CateringOrder(TimeStampedModel):
    provider = models.ForeignKey(
        CateringProvider, verbose_name=_('Catering provider'), related_name='catering_orders', on_delete=models.PROTECT
    )
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
        ordering = ('id',)

    def __str__(self):
        return 'catering order for %s' % self.reservation

    def get_provider(self):
        return self.provider

    def get_notification_context(self, language_code):
        with translation.override(language_code):
            serving_time = self.serving_time
            if not serving_time:
                serving_time = self.reservation.begin.astimezone(self.reservation.resource.unit.get_tz())
            context = {
                'resource': self.reservation.resource.name,
                'reservation': self.reservation,
                'unit': self.reservation.resource.unit.name if self.reservation.resource.unit else '',
                'serving_time': formats.date_format(serving_time, 'TIME_FORMAT'),
                'invoicing_data': self.invoicing_data,
                'message': self.message,
                'order_lines': [],
            }

            for order_line in self.order_lines.all():
                context['order_lines'].append({
                    'product': order_line.product.name,
                    'quantity': order_line.quantity,
                    'category': order_line.product.category.name,
                })

        return context

    def _send_notification(self, notification_type, request=None):
        provider = self.get_provider()
        email = provider.notification_email if provider else None
        if not email:
            return

        context = self.get_notification_context(DEFAULT_LANG)
        try:
            rendered_notification = render_notification_template(notification_type, context, DEFAULT_LANG)
        except NotificationTemplateException as e:
            logger.error(e, exc_info=True, extra={'request': request})
            return

        send_respa_mail(
            email,
            rendered_notification['subject'],
            rendered_notification['body'],
            rendered_notification['html_body']
        )

    def send_created_notification(self, request=None):
        self._send_notification(NotificationType.CATERING_ORDER_CREATED, request)

    def send_modified_notification(self, request=None):
        self._send_notification(NotificationType.CATERING_ORDER_MODIFIED, request)

    def send_deleted_notification(self, request=None):
        self._send_notification(NotificationType.CATERING_ORDER_DELETED, request)


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
