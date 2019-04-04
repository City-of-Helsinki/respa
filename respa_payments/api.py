from django.utils.translation import ugettext_lazy as _
from django.utils.module_loading import import_string
from django.utils import timezone
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.http import HttpResponseRedirect
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status, serializers, viewsets
from resources.models.resource import Resource, DurationSlot
from resources.api.base import register_view
from resources.api.resource import ResourceSerializer, ResourceDetailsSerializer, DurationSlotSerializer
from respa_payments.models import Order, Sku
from respa_payments import settings



class SkuSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sku
        fields = '__all__'


class PaymentDurationSlotSerializer(DurationSlotSerializer):
    skus = SkuSerializer(many=True)
    class Meta:
        model = DurationSlot
        fields = ('id', 'duration', 'skus',)


class PaymentResourceSerializer(ResourceSerializer):
    duration_slots = PaymentDurationSlotSerializer(many=True)
    class Meta:
        model = Resource
        exclude = ('reservation_requested_notification_extra', 'reservation_confirmed_notification_extra',
                   'access_code_type', 'reservation_metadata_set')


class PaymentResourceDetailsSerializer(ResourceDetailsSerializer):
    duration_slots = PaymentDurationSlotSerializer(many=True)


class OrderSerializer(serializers.ModelSerializer):
    begin = serializers.CharField(source='reservation.begin', read_only=True)
    end = serializers.CharField(source='reservation.end', read_only=True)
    reserver_name = serializers.CharField(source='reservation.reserver_name', read_only=True)
    reserver_id = serializers.CharField(source='reservation.reserver_id', read_only=True)
    reserver_email_address = serializers.CharField(source='reservation.reserver_email_address', read_only=True)
    reserver_phone_number = serializers.CharField(source='reservation.reserver_phone_number', read_only=True)
    reserver_address_street = serializers.CharField(source='reservation.reserver_address_street', read_only=True)
    reserver_address_zip = serializers.CharField(source='reservation.reserver_address_zip', read_only=True)
    reserver_address_city = serializers.CharField(source='reservation.reserver_address_city', read_only=True)
    company = serializers.CharField(source='reservation.company', read_only=True)
    billing_address_street = serializers.CharField(source='reservation.billing_address_street', read_only=True)
    billing_address_zip = serializers.CharField(source='reservation.billing_address_zip', read_only=True)
    billing_address_city = serializers.CharField(source='reservation.billing_address_city', read_only=True)
    product_id = serializers.CharField(source='sku.id', read_only=True)
    product = serializers.CharField(source='sku.name', read_only=True)
    price = serializers.CharField(source='sku.price', read_only=True)
    vat = serializers.CharField(source='sku.vat', read_only=True)
    class Meta:
        model = Order
        fields = ('id', 'sku', 'reservation', 'order_process_started', 'order_process_success', 'order_process_failure', 
                  'order_process_notified', 'payment_service_timestamp', 'payment_service_amount', 'payment_service_currency', 
                  'payment_service_status', 'payment_service_success', 'payment_service_method', 'payment_service_return_authcode',
                  'begin', 'end', 'reserver_name', 'reserver_id', 'reserver_email_address', 'reserver_phone_number', 'reserver_address_street', 
                  'reserver_address_zip', 'reserver_address_city', 'company', 'billing_address_street', 'billing_address_zip', 'billing_address_city', 
                  'product', 'product_id', 'price', 'vat', 'verification_code',)


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    queryset = Order.objects.all()

register_view(OrderViewSet, 'orders')


class OrderPostView(APIView):
    permission_classes = (permissions.AllowAny,)

    def __init__(self):
        self.payment_integration = import_string(settings.INTEGRATION_CLASS)

    def post(self, request):
        return self.payment_integration(request=request).order_post()


class OrderCallbackView(APIView):
    permission_classes = (permissions.AllowAny,)

    def __init__(self):
        self.payment_integration = import_string(settings.INTEGRATION_CLASS)

    def get(self, request):
        return self.payment_integration(request=request).payment_callback()