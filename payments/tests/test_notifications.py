import pytest
from django.core import mail
from django.test import override_settings
from django.utils import translation

from django_ilmoitin.models import NotificationTemplate
from resources.notifications import NotificationType
from notifications.tests.utils import check_received_mail_exists
from payments.utils import get_price_period_display
from resources.models import Reservation

from ..models import Order


def localize_decimal(d):
    return str(d).replace('.', ',')


def get_body_with_all_template_vars():
    template_vars = (
        'order.id',
        'order.created_at',
        'order.price',
        'order_line.price',
        'order_line.quantity',
        'order_line.unit_price',
        'product.id',
        'product.name',
        'product.description',
        'product.type',
        'product.type_display',
        'product.price_type',
        'product.price_type_display',
        'product.price_period',
        'product.price_period_display',
    )
    body = '{% set order_line=order.order_lines[0] %}{% set product=order_line.product %}\n'
    for template_var in template_vars:
        body += '{{ %s }}\n' % template_var
    return body


def get_expected_strings(order):
    order_line = order.order_lines.first()
    product = order_line.product
    return (
        order.order_number,
        str(order.created_at.year),
        localize_decimal(order.get_price()),
        localize_decimal(order_line.get_price()),
        str(order_line.quantity),
        localize_decimal(order_line.get_unit_price()),
        product.product_id,
        product.name,
        product.description,
        product.type,
        product.get_type_display(),
        product.price_type,
        product.get_price_type_display(),
        str(product.price_period),
        str(get_price_period_display(product.price_period)),
    )


@pytest.fixture(autouse=True)
def reservation_created_notification():
    NotificationTemplate.objects.filter(type=NotificationType.RESERVATION_CREATED).delete()
    with translation.override('fi'):
        return NotificationTemplate.objects.create(
            type=NotificationType.RESERVATION_CREATED,
            subject='Reservation created subject.',
            body_text='Reservation created body. \n' + get_body_with_all_template_vars()
        )


@pytest.fixture(autouse=True)
def reservation_cancelled_notification():
    NotificationTemplate.objects.filter(type=NotificationType.RESERVATION_CANCELLED).delete()
    with translation.override('fi'):
        return NotificationTemplate.objects.create(
            type=NotificationType.RESERVATION_CANCELLED,
            subject='Reservation cancelled subject.',
            body_text='Reservation cancelled body. \n' + get_body_with_all_template_vars()
        )


@pytest.mark.django_db
@override_settings(RESPA_MAILS_ENABLED=True)
def test_reservation_created_notification(order_with_products):
    user = order_with_products.reservation.user
    user.preferred_language = 'fi'
    user.save()

    order_with_products.set_state(Order.CONFIRMED)

    assert len(mail.outbox) == 1
    check_received_mail_exists(
        'Reservation created subject.',
        order_with_products.reservation.user.email,
        get_expected_strings(order_with_products),
    )


@pytest.mark.parametrize('order_state, notification_expected', (
    (Order.REJECTED, False),
    (Order.EXPIRED, False),
    (Order.CANCELLED, True),
))
@pytest.mark.django_db
@override_settings(RESPA_MAILS_ENABLED=True)
def test_reservation_cancelled_notification(order_with_products, order_state, notification_expected):
    user = order_with_products.reservation.user
    user.preferred_language = 'fi'
    user.save()
    if order_state == Order.CANCELLED:
        Reservation.objects.filter(id=order_with_products.reservation.id).update(state=Reservation.CONFIRMED)
        Order.objects.filter(id=order_with_products.id).update(state=Order.CONFIRMED)
        order_with_products.refresh_from_db()

    order_with_products.set_state(order_state)

    if notification_expected:
        assert len(mail.outbox) == 1
        check_received_mail_exists(
            'Reservation cancelled subject.',
            order_with_products.reservation.user.email,
            get_expected_strings(order_with_products),
        )
    else:
        assert len(mail.outbox) == 0
