from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
from jinja2 import StrictUndefined
from jinja2.exceptions import TemplateError
from jinja2.sandbox import SandboxedEnvironment
from parler.models import TranslatableModel, TranslatedFields
from parler.utils.context import switch_language

DEFAULT_LANG = settings.LANGUAGES[0][0]


class NotificationType:
    RESERVATION_REQUESTED = 'reservation_requested'
    RESERVATION_REQUESTED_OFFICIAL = 'reservation_requested_official'
    RESERVATION_CANCELLED = 'reservation_cancelled'
    RESERVATION_CONFIRMED = 'reservation_confirmed'
    RESERVATION_DENIED = 'reservation_denied'
    RESERVATION_CREATED_WITH_ACCESS_CODE = 'reservation_created_with_access_code'
    CATERING_ORDER_CREATED = 'catering_order_created'
    CATERING_ORDER_MODIFIED = 'catering_order_modified'
    CATERING_ORDER_DELETED = 'catering_order_deleted'


class NotificationTemplateException(Exception):
    pass


class NotificationTemplate(TranslatableModel):
    NOTIFICATION_TYPE_CHOICES = (
        (NotificationType.RESERVATION_REQUESTED, _('Reservation requested')),
        (NotificationType.RESERVATION_REQUESTED_OFFICIAL, _('Reservation requested official')),
        (NotificationType.RESERVATION_CANCELLED, _('Reservation cancelled')),
        (NotificationType.RESERVATION_CONFIRMED, _('Reservation confirmed')),
        (NotificationType.RESERVATION_DENIED, _('Reservation_denied')),
        (NotificationType.RESERVATION_CREATED_WITH_ACCESS_CODE, _('Reservation created with access code')),
        (NotificationType.CATERING_ORDER_CREATED, _('Catering order created')),
        (NotificationType.CATERING_ORDER_MODIFIED, _('Catering order modified')),
        (NotificationType.CATERING_ORDER_DELETED, _('Catering order deleted')),
    )

    type = models.CharField(
        verbose_name=_('Type'), choices=NOTIFICATION_TYPE_CHOICES, max_length=100, unique=True, db_index=True
    )

    translations = TranslatedFields(
        short_message=models.TextField(
            verbose_name=_('Short message'), blank=True, help_text=_('Short notification text for e.g. SMS messages')
        ),
        subject=models.CharField(
            verbose_name=_('Subject'), max_length=200, help_text=_('Subject for email notifications')
        ),
        body=models.TextField(verbose_name=_('body'), help_text=_('Text body for email notifications'))
    )

    class Meta:
        verbose_name = _('Notification template')
        verbose_name_plural = _('Notification templates')

    def __str__(self):
        for t in self.NOTIFICATION_TYPE_CHOICES:
            if t[0] == self.type:
                return str(t[1])
        return 'N/A'


def render_notification_template(notification_type, context, language_code=DEFAULT_LANG):
    """
    Render a notification template with given context

    Returns a dict containing all content fields of the template. Example:

    {'short_message': 'foo', 'subject': 'bar', 'body': 'baz'}

    """
    try:
        template = NotificationTemplate.objects.get(type=notification_type)
    except NotificationTemplate.DoesNotExist as e:
        raise NotificationTemplateException(e) from e

    env = SandboxedEnvironment(trim_blocks=True, lstrip_blocks=True, undefined=StrictUndefined)

    with switch_language(template, language_code):
        try:
            return {
                attr: env.from_string(getattr(template, attr)).render(context)
                for attr in ('short_message', 'subject', 'body')
            }
        except TemplateError as e:
            raise NotificationTemplateException(e) from e
