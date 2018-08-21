import logging

from django.conf import settings
from django.db import models
from django.utils import translation
from django.utils.translation import ugettext_lazy as _
from django.utils.formats import date_format
from jinja2 import StrictUndefined
from jinja2.exceptions import TemplateError
from jinja2.sandbox import SandboxedEnvironment
from parler.models import TranslatableModel, TranslatedFields
from parler.utils.context import switch_language

DEFAULT_LANG = settings.LANGUAGES[0][0]

logger = logging.getLogger('respa.notifications')


class NotificationType:
    RESERVATION_REQUESTED = 'reservation_requested'
    RESERVATION_REQUESTED_OFFICIAL = 'reservation_requested_official'
    RESERVATION_CANCELLED = 'reservation_cancelled'
    RESERVATION_CONFIRMED = 'reservation_confirmed'
    RESERVATION_DENIED = 'reservation_denied'
    RESERVATION_CREATED = 'reservation_created'
    RESERVATION_CREATED_WITH_ACCESS_CODE = 'reservation_created_with_access_code'
    CATERING_ORDER_CREATED = 'catering_order_created'
    CATERING_ORDER_MODIFIED = 'catering_order_modified'
    CATERING_ORDER_DELETED = 'catering_order_deleted'

    RESERVATION_COMMENT_CREATED = 'reservation_comment_created'
    CATERING_ORDER_COMMENT_CREATED = 'catering_order_comment_created'


class NotificationTemplateException(Exception):
    pass


class NotificationTemplate(TranslatableModel):
    NOTIFICATION_TYPE_CHOICES = (
        (NotificationType.RESERVATION_REQUESTED, _('Reservation requested')),
        (NotificationType.RESERVATION_REQUESTED_OFFICIAL, _('Reservation requested official')),
        (NotificationType.RESERVATION_CANCELLED, _('Reservation cancelled')),
        (NotificationType.RESERVATION_CONFIRMED, _('Reservation confirmed')),
        (NotificationType.RESERVATION_CREATED, _('Reservation created')),
        (NotificationType.RESERVATION_DENIED, _('Reservation denied')),
        (NotificationType.RESERVATION_CREATED_WITH_ACCESS_CODE, _('Reservation created with access code')),
        (NotificationType.CATERING_ORDER_CREATED, _('Catering order created')),
        (NotificationType.CATERING_ORDER_MODIFIED, _('Catering order modified')),
        (NotificationType.CATERING_ORDER_DELETED, _('Catering order deleted')),
        (NotificationType.RESERVATION_COMMENT_CREATED, _('Reservation comment created')),
        (NotificationType.CATERING_ORDER_COMMENT_CREATED, _('Catering order comment created')),
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


def reservation_time(res):
    if isinstance(res, dict):
        return res['time_range']
    return res.format_time()


def format_datetime(dt):
    current_language = translation.get_language()
    if current_language == 'fi':
        # ma 1.1.2017 klo 12.00
        dt_format = r'D j.n.Y \k\l\o G.i'
    else:
        # default to English
        dt_format = r'D j/n/Y G:i'

    return date_format(dt, dt_format)


def format_datetime_tz(dt, tz):
    dt = dt.astimezone(tz)
    return format_datetime(dt)


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
    env.filters['reservation_time'] = reservation_time
    env.filters['format_datetime'] = format_datetime
    env.filters['format_datetime_tz'] = format_datetime_tz

    logger.info('Rendering template for notification %s' % notification_type)
    with switch_language(template, language_code):
        try:
            return {
                attr: env.from_string(getattr(template, attr)).render(context)
                for attr in ('short_message', 'subject', 'body')
            }
        except TemplateError as e:
            raise NotificationTemplateException(e) from e
