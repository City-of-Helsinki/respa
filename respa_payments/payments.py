import uuid
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.utils import timezone
from django.http import HttpResponseRedirect
from rest_framework import status
from respa_payments import settings
from rest_framework import serializers
from rest_framework.response import Response
from respa_payments.api import OrderSerializer
from respa_payments.models import Order


class PaymentIntegration(object):
    def __init__(self, **kwargs):
        self.request = kwargs.get('request', None)
        self.api_url = settings.PAYMENT_API_URL
        self.url_notify = settings.URL_NOTIFY
        self.url_failed = settings.URL_FAILED
        self.url_cancel = settings.URL_CANCEL
        self.url_redirect_callback = settings.URL_REDIRECT_CALLBACK

    def construct_order_post(self, order):
        self.url_success = '{}?id={}&verification_code={}'.format(
            settings.URL_SUCCESS, order.get('id', None), order.get('verification_code', None))
        return order

    def construct_payment_callback(self):
        callback_data = {
            'redirect_url': self.url_redirect_callback or '',
            'order_process_success': timezone.now(),
        }
        return callback_data

    def order_post(self):
        order_serializer = OrderSerializer(data={'reservation': self.request.data.get(
            'reservation_id', None), 'sku': self.request.data.get('sku_id', None), 'verification_code': str(uuid.uuid4())})
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
        except Order.DoesNotExist:
            return HttpResponseRedirect(callback_data.get('redirect_url') + '?errors=[\'Requested order is not valid.\']')

        order_serializer = OrderSerializer(order, data=callback_data, partial=True)
        if self.is_valid():
            if order_serializer.is_valid():
                order_serializer.save()
                return HttpResponseRedirect(callback_data.get('redirect_url') + 'reservation?id={}&resource={}&code={}'.format(
                    order.id,
                    order.reservation.resource.id,
                    order.verification_code
                ))
            return HttpResponseRedirect(callback_data.get('redirect_url') + '?errors=' + str(order_serializer.errors))
        return HttpResponseRedirect(callback_data.get('redirect_url') + '?errors=[\'Requested order is not valid.\']')

    def is_valid(self):
        return True
