from django_ilmoitin.registry import notifications
from django.utils.translation import ugettext_lazy as _


class NotificationType:
    RESERVATION_REQUESTED = 'reservation_requested'
    RESERVATION_REQUESTED_OFFICIAL = 'reservation_requested_official'
    RESERVATION_CANCELLED = 'reservation_cancelled'
    RESERVATION_CONFIRMED = 'reservation_confirmed'
    RESERVATION_DENIED = 'reservation_denied'
    RESERVATION_CREATED = 'reservation_created'

    # If the access code is known at reservation time, this notification
    # type is used.
    RESERVATION_CREATED_WITH_ACCESS_CODE = 'reservation_created_with_access_code'

    # In some cases, the access code is known only some time after the
    # reservation is made. A separate notification type is used so that
    # we don't confuse the user with "new reservation created"-style
    # messaging.
    RESERVATION_ACCESS_CODE_CREATED = 'reservation_access_code_created'

    CATERING_ORDER_CREATED = 'catering_order_created'
    CATERING_ORDER_MODIFIED = 'catering_order_modified'
    CATERING_ORDER_DELETED = 'catering_order_deleted'

    RESERVATION_COMMENT_CREATED = 'reservation_comment_created'
    CATERING_ORDER_COMMENT_CREATED = 'catering_order_comment_created'


# Register notification types with django-ilmoitin
notifications.register(NotificationType.RESERVATION_REQUESTED, _('Reservation requested'))
notifications.register(NotificationType.RESERVATION_REQUESTED_OFFICIAL, _('Reservation requested official'))
notifications.register(NotificationType.RESERVATION_CANCELLED, _('Reservation cancelled'))
notifications.register(NotificationType.RESERVATION_CONFIRMED, _('Reservation confirmed'))
notifications.register(NotificationType.RESERVATION_CREATED, _('Reservation created'))
notifications.register(NotificationType.RESERVATION_DENIED, _('Reservation denied'))
notifications.register(NotificationType.RESERVATION_CREATED_WITH_ACCESS_CODE, _('Reservation created with access code'))
notifications.register(NotificationType.RESERVATION_ACCESS_CODE_CREATED, _('Access code was created for a reservation'))
notifications.register(NotificationType.CATERING_ORDER_CREATED, _('Catering order created'))
notifications.register(NotificationType.CATERING_ORDER_MODIFIED, _('Catering order modified'))
notifications.register(NotificationType.CATERING_ORDER_DELETED, _('Catering order deleted'))
notifications.register(NotificationType.RESERVATION_COMMENT_CREATED, _('Reservation comment created'))
notifications.register(NotificationType.CATERING_ORDER_COMMENT_CREATED, _('Catering order comment created'))