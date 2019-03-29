import uuid
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.utils import timezone
from django.http import HttpResponseRedirect
from rest_framework import status, serializers
from rest_framework.response import Response
from resources.models import Reservation
from respa_payments import settings
from respa_payments.api import OrderSerializer
from respa_payments.models import Order


class PaymentIntegration(object):
    def __init__(self, **kwargs):
        self.request = kwargs.get('request', None)
        self.api_url = settings.PAYMENT_API_URL
        self.url_redirect_callback = settings.URL_REDIRECT_CALLBACK
        self.url_notify = settings.URL_NOTIFY

    def construct_order_post(self, order):
        self.url_success = '{}?id={}&verification_code={}'.format(
            settings.URL_SUCCESS, order.get('id', None), order.get('verification_code', None))
        self.url_cancel = '{}?id={}&verification_code={}'.format(
            settings.URL_CANCEL, order.get('id', None), order.get('verification_code', None))
        return order

    def construct_payment_callback(self):
        callback_data = {
            'redirect_url': self.url_redirect_callback or '',
            'order_process_success': timezone.now(),
        }
        return callback_data

    def order_post(self):
        if self.request.user.is_staff:
            return self.skip_payment()
        order_serializer = OrderSerializer(data={
            'order_process_started': timezone.now(),
            'reservation': self.request.data.get('reservation_id', None),
            'sku': self.request.data.get('sku_id', None),
            'verification_code': str(uuid.uuid4())
        })
        if order_serializer.is_valid():
            order = order_serializer.save()
            post_data = self.construct_order_post(OrderSerializer(order).data)
            return Response(post_data, status=status.HTTP_201_CREATED)
        return Response(order_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def payment_callback(self):
        callback_data = self.construct_payment_callback()
        order_id = self.request.GET.get('id')
        verification_code = self.request.GET.get('verification_code')
        try:
            order = Order.objects.get(pk=order_id, verification_code=verification_code)
            reservation = order.reservation
        except Order.DoesNotExist:
            return HttpResponseRedirect(callback_data.get('redirect_url') + 'requested-order-not-valid')

        order_serializer = OrderSerializer(order, data=callback_data)
        if order_serializer.is_valid() and callback_data.get('payment_service_success', False):
            reservation.set_state(Reservation.CONFIRMED, self.request.user)
            order_serializer.save()
        else:
            reservation.comments = 'Payment was unsuccesful.'
            reservation.set_state(Reservation.DENIED, self.request.user)  # set_state() saves the reservation
            order.order_process_failure = timezone.now()
            order.order_process_log = str(order_serializer.errors)
            if not callback_data.get('payment_service_success', False):
                order.order_process_log = 'Payment cancelled.'
            order.save()
            return HttpResponseRedirect(callback_data.get('redirect_url') + 'resources/{}'.format(
                order.reservation.resource.id,
            ))
        return HttpResponseRedirect(
            callback_data.get('redirect_url')
            + 'reservation?id={}&reservation={}&resource={}'.format(
                order.id,
                order.reservation.id,
                order.reservation.resource.id,
            ))

    def skip_payment(self):
        reservation = Reservation.objects.get(pk=self.request.data.get('reservation_id', None))
        reservation.approver = self.request.user
        reservation.comments = 'Reservation created by staff.'
        reservation.set_state(Reservation.CONFIRMED, self.request.user)  # set_state() saves the reservation
        callback_data = self.construct_payment_callback()
        return HttpResponseRedirect(
            callback_data.get('redirect_url')
            + 'reservation?reservation={}&resource={}'.format(
                reservation.id,
                reservation.resource.id,
            ))
