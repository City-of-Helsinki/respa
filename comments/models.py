import logging
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.db import models
from django.contrib.gis.db.models import Q
from django.utils.translation import ugettext_lazy as _
from caterings.models import CateringOrder
from resources.models import Reservation, Resource
from resources.models.utils import send_respa_mail
from notifications.models import (
    DEFAULT_LANG, render_notification_template, NotificationTemplateException, NotificationType
)


logger = logging.getLogger(__name__)


COMMENTABLE_MODELS = {
    'reservation': Reservation,
}

if getattr(settings, 'RESPA_CATERINGS_ENABLED', False):
    COMMENTABLE_MODELS.update({
        'catering_order': CateringOrder,
    })


def get_commentable_content_types():
    return ContentType.objects.get_for_models(*COMMENTABLE_MODELS.values()).values()


class CommentQuerySet(models.QuerySet):
    def can_view(self, user):
        if not user.is_authenticated:
            return self.none()

        reservation_resources = Resource.objects.with_perm('can_access_reservation_comments', user)
        allowed_reservation_ids = Reservation.objects.filter(
            Q(resource__in=reservation_resources) | Q(user=user)
        ).values_list('id', flat=True)

        catering_resources = Resource.objects.with_perm('can_view_reservation_catering_orders', user)
        allowed_catering_order_ids = CateringOrder.objects.filter(
            Q(reservation__resource__in=catering_resources) | Q(reservation__user=user)
        ).values_list('id', flat=True)

        reservation_content_type = ContentType.objects.get_for_model(Reservation)
        catering_order_content_type = ContentType.objects.get_for_model(CateringOrder)

        return self.filter(
            Q(created_by=user) |
            (Q(content_type=reservation_content_type) & Q(object_id__in=allowed_reservation_ids)) |
            (Q(content_type=catering_order_content_type) & Q(object_id__in=allowed_catering_order_ids))
        )


class Comment(models.Model):
    created_at = models.DateTimeField(verbose_name=_('Time of creation'), auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('Created by'),
                                   null=True, blank=True, related_name='%(class)s_created',
                                   on_delete=models.PROTECT)
    text = models.TextField(verbose_name=_('Text'))
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to=lambda: {'id__in': (ct.id for ct in get_commentable_content_types())}
    )
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    objects = CommentQuerySet.as_manager()

    class Meta:
        ordering = ('id',)
        verbose_name = _('Comment')
        verbose_name_plural = _('Comments')
        index_together = (('content_type', 'object_id'),)

    def __str__(self):
        author = self.created_by.get_display_name() if self.created_by else 'Unknown author'
        text = self.text if len(self.text) < 40 else self.text[:37] + '...'
        return '%s %s %s: %s' % (self.content_type.model, self.object_id, author, text)

    @staticmethod
    def can_user_comment_object(user, target_object):
        if not (user and user.is_authenticated):
            return False

        target_model = target_object.__class__
        if target_model not in COMMENTABLE_MODELS.values():
            return False

        if target_model == Reservation:
            if user == target_object.user:
                return True
            if target_object.resource.can_access_reservation_comments(user):
                return True
        elif target_model == CateringOrder:
            if user == target_object.reservation.user:
                return True
            if target_object.reservation.resource.can_view_catering_orders(user):
                return True
        return False

    def get_notification_context(self, language_code):
        target_object = self.content_object
        target_model = target_object.__class__
        assert target_model in COMMENTABLE_MODELS.values()

        target_type = next(api_name for api_name, model in COMMENTABLE_MODELS.items() if model == target_model)
        context = dict(
            text=self.text,
            target_type=target_type,
            created_at=self.created_at
        )
        if self.created_by:
            context['created_by'] = dict(display_name=self.created_by.get_display_name())
        else:
            context['created_by'] = None

        if target_model == Reservation:
            context['reservation'] = target_object.get_notification_context(language_code)
            tz = target_object.resource.unit.get_tz()
        elif target_model == CateringOrder:
            context['catering_order'] = target_object.get_notification_context(language_code)
            tz = target_object.reservation.resource.unit.get_tz()

        # Use local timezones by default
        context['created_at'] = context['created_at'].astimezone(tz)

        return context

    def _send_notification(self, request=None):
        target_object = self.content_object
        target_model = target_object.__class__
        assert target_model in COMMENTABLE_MODELS.values()

        if target_model == CateringOrder:
            catering_provider = target_object.get_provider()
            email = catering_provider.notification_email if catering_provider else None
            reserver = target_object.reservation.user
            notification_type = NotificationType.CATERING_ORDER_COMMENT_CREATED
        elif target_model == Reservation:
            unit = target_object.resource.unit
            email = unit.manager_email if unit.manager_email else None
            reserver = target_object.user
            notification_type = NotificationType.RESERVATION_COMMENT_CREATED

        context = self.get_notification_context(DEFAULT_LANG)
        try:
            rendered_notification = render_notification_template(notification_type, context, DEFAULT_LANG)
        except NotificationTemplateException as e:
            logger.error(e, exc_info=True, extra={'request': request})
            return

        if email:
            send_respa_mail(
                email,
                rendered_notification['subject'],
                rendered_notification['body'],
                rendered_notification['html_body']
            )
        if self.created_by != reserver and reserver.email:
            send_respa_mail(
                reserver.email,
                rendered_notification['subject'],
                rendered_notification['body'],
                rendered_notification['html_body']
            )

    def send_created_notification(self, request=None):
        self._send_notification(request)
