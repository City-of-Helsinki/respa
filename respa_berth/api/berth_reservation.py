import arrow
import django_filters
import re
import hashlib
import logging
from arrow.parser import ParserError
from django.core.exceptions import PermissionDenied, ImproperlyConfigured, SuspiciousOperation, ValidationError
from django.utils import timezone
from rest_framework import viewsets, serializers, filters, exceptions, permissions, pagination, status
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from munigeo import api as munigeo_api
from resources.models import Reservation
from respa_berth.api.reservation import ReservationSerializer
from respa_berth.api.berth import BerthSerializer
from respa_berth.models.berth_reservation import BerthReservation
from respa_berth.models.purchase import Purchase
from resources.api.base import TranslatedModelSerializer, register_view
from respa_berth.utils.utils import RelatedOrderingFilter
from django.utils.translation import ugettext_lazy as _
from respa_berth.models.berth import Berth, GroundBerthPrice
from resources.models.resource import Resource, ResourceType
from resources.models.unit import Unit
from rest_framework.views import APIView
from django.conf import settings
from django.http import HttpResponseRedirect
from datetime import timedelta
from django.db.models import Q
from rest_framework.exceptions import ParseError
from respa_berth import tasks
from respa_berth.models.sms_message import SMSMessage
from respa_berth.paytrailpayments import *

LOG = logging.getLogger(__name__)

class BerthReservationSerializer(TranslatedModelSerializer, munigeo_api.GeoModelSerializer):
    reservation = ReservationSerializer(required=True)
    is_paid = serializers.BooleanField(required=False)
    reserver_ssn = serializers.CharField(required=False)
    berth = BerthSerializer(required=True)
    has_ended = serializers.SerializerMethodField()
    is_renewed = serializers.SerializerMethodField()
    has_started = serializers.SerializerMethodField()
    reserved_by_citizen = serializers.SerializerMethodField()
    resend_renewal = serializers.BooleanField(required=False)
    partial = True

    class Meta:
        model = BerthReservation
        fields = ['id', 'berth', 'is_paid', 'reserver_ssn', 'reservation', 'state_updated_at', 'is_paid_at', 'key_returned', 'key_returned_at', 'has_ended', 'is_renewed', 'has_started', 'resend_renewal', 'reserved_by_citizen']

    def get_reserved_by_citizen(self, obj):
        return hasattr(obj, 'purchase') and obj.purchase != None

    def get_has_started(self, obj):
        return obj.reservation.begin > timezone.now()

    def get_has_ended(self, obj):
        return obj.reservation.end < timezone.now()

    def get_is_renewed(self, obj):
        return obj.child.filter(reservation__state=Reservation.CONFIRMED).exists()

    def validate(self, data):
        request_user = self.context['request'].user
        reservation_data = data.get('reservation')
        berth_reservation_id = self.context['request'].data.get('id')

        if reservation_data != None:
            resource = reservation_data.get('resource')
            if resource:
                overlaps_existing = False
                if berth_reservation_id:
                    overlaps_existing = BerthReservation.objects.filter(reservation__begin__lt=reservation_data.get('end'), reservation__end__gt=reservation_data.get('begin'), berth=resource.berth, reservation__state=Reservation.CONFIRMED).exclude(pk=berth_reservation_id).exists()
                else:
                    overlaps_existing = BerthReservation.objects.filter(reservation__begin__lt=reservation_data.get('end'), reservation__end__gt=reservation_data.get('begin'), berth=resource.berth, reservation__state=Reservation.CONFIRMED).exists()

                if overlaps_existing:
                    raise serializers.ValidationError(_('New reservation overlaps existing reservation'))

                # if request_user.is_staff:
                #     two_minutes_ago = timezone.now() - timedelta(minutes=2)
                #     if resource.berth.reserving and resource.berth.reserving > two_minutes_ago:
                #         raise serializers.ValidationError(_('Someone is reserving the berth at the moment'))

        return data

    def create(self, validated_data):
        request_user = self.context['request'].user
        request_reservation_data = validated_data.pop('reservation')
        reservation_data = {}

        if not request_user.is_staff:
            reservation_data['begin'] = request_reservation_data.get('begin')
            reservation_data['end'] = request_reservation_data.get('end')
            reservation_data['reserver_name'] = request_reservation_data.get('reserver_name', '')
            reservation_data['reserver_email_address'] = request_reservation_data.get('reserver_email_address', '')
            reservation_data['reserver_phone_number'] = request_reservation_data.get('reserver_phone_number', '')
            reservation_data['reserver_address_street'] = request_reservation_data.get('reserver_address_street', '')
            reservation_data['reserver_address_zip'] = request_reservation_data.get('reserver_address_zip', '')
            reservation_data['reserver_address_city'] = request_reservation_data.get('reserver_address_city', '')
            reservation_data['state'] = Reservation.CONFIRMED
            reservation_data['resource'] = request_reservation_data.get('resource')
        else:
            reservation_data = request_reservation_data

        reservation = Reservation.objects.create(**reservation_data)
        resource = reservation_data['resource']
        resource.reservable = False
        resource.save()
        validated_data.pop('berth')
        key_returned = resource.berth.type == Berth.DOCK
        berthReservation = BerthReservation.objects.create(reservation=reservation, key_returned=key_returned, berth=resource.berth, **validated_data)
        return berthReservation

    def update(self, instance, validated_data):
        if self.context['request'].method == 'PUT':
            return self.update_reservation_info(instance, validated_data)
        elif self.context['request'].method == 'PATCH':
            return self.update_reservation_status(instance, validated_data)

    def update_reservation_info(self, instance, validated_data):
        reservation_data = validated_data.pop('reservation')
        reservation = instance.reservation

        reservation.begin = reservation_data.get('begin', reservation.begin)
        reservation.end = reservation_data.get('end', reservation.end)
        reservation.event_description = reservation_data.get('event_description', reservation.event_description)
        reservation.reserver_name = reservation_data.get('reserver_name', reservation.reserver_name)
        reservation.reserver_email_address = reservation_data.get('reserver_email_address', reservation.reserver_email_address)
        reservation.reserver_phone_number = reservation_data.get('reserver_phone_number', reservation.reserver_phone_number)
        reservation.reserver_address_street = reservation_data.get('reserver_address_street', reservation.reserver_address_street)
        reservation.reserver_address_zip = reservation_data.get('reserver_address_zip', reservation.reserver_address_zip)
        reservation.reserver_address_city = reservation_data.get('reserver_address_city', reservation.reserver_address_city)
        reservation.save()

        return instance

    def update_reservation_status(self, instance, validated_data):
        is_paid = validated_data.get('is_paid')
        key_returned = validated_data.get('key_returned')
        resend_renewal = validated_data.get('resend_renewal')
        if is_paid != None:
            if is_paid:
                instance.is_paid_at = timezone.now()
                instance.is_paid = True

            else:
                instance.is_paid_at = None
                instance.is_paid = False
        elif key_returned != None:
            if key_returned:
                instance.key_returned_at = timezone.now()
                instance.key_returned = True
            else:
                instance.key_returned_at = None
                instance.key_returned = False
        elif resend_renewal:
            tasks.send_initial_renewal_notification.delay(instance.pk)
        else:
            instance.cancel_reservation(self.context['request'].user)

        instance.save()

        return instance

    def to_representation(self, instance):
        data = super(BerthReservationSerializer, self).to_representation(instance)
        return data

    def to_internal_value(self, data):
        # clean up inconsistent data sent by UI
        if 'reservation' in data and 'user' in data['reservation']:
            if not data['reservation']['user']:
                del data['reservation']['user']
        return super().to_internal_value(data)

    def validate_reserver_ssn(self, value):
        number_array = re.findall(r'\d+', value[:-1])
        if not number_array or len(value) != 11:
            raise serializers.ValidationError(_('Social security number not valid'))
        ssn_numbers = int(''.join(str(x) for x in number_array))
        test_array = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D',
         'E', 'F', 'H', 'J', 'K', 'L', 'M', 'N', 'P', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y']

        check_char = test_array[ssn_numbers % 31]

        if not value.endswith(check_char):
            raise serializers.ValidationError(_('Social security number not valid'))
        return value

class BerthReservationGroundBerthSerializer(BerthReservationSerializer):
    reservation = serializers.DictField(required=True)
    berth = serializers.DictField(required=True)

    def validate(self, data):
        request_user = self.context['request'].user

        if data['berth']['type'] != Berth.GROUND and request_user.is_staff and data.get('reservation'):
            two_minutes_ago = timezone.now() - timedelta(minutes=2)
            reservation_data = data.get('reservation')
            resource = reservation_data['resource']
            if resource.berth.reserving and resource.berth.reserving > two_minutes_ago:
                raise serializers.ValidationError(_('Someone is reserving the berth at the moment'))

        return data

    def to_representation(self, instance):
        serializer = BerthReservationSerializer(instance, context=self.context)
        return serializer.data

    def create(self, validated_data):
        request_user = self.context['request'].user
        request_reservation_data = validated_data.pop('reservation')

        reservation_data = {}

        if not request_user.is_staff:
            reservation_data['begin'] = request_reservation_data.get('begin')
            reservation_data['end'] = request_reservation_data.get('end')
            reservation_data['reserver_name'] = request_reservation_data.get('reserver_name', '')
            reservation_data['reserver_email_address'] = request_reservation_data.get('reserver_email_address', '')
            reservation_data['reserver_phone_number'] = request_reservation_data.get('reserver_phone_number', '')
            reservation_data['reserver_address_street'] = request_reservation_data.get('reserver_address_street', '')
            reservation_data['reserver_address_zip'] = request_reservation_data.get('reserver_address_zip', '')
            reservation_data['reserver_address_city'] = request_reservation_data.get('reserver_address_city', '')
            reservation_data['state'] = Reservation.CONFIRMED
        else:
            reservation_data = request_reservation_data

        if not reservation_data.get('begin') or not reservation_data.get('end'):
            reservation_data['begin'] = timezone.now()
            reservation_data['end'] = timezone.now() + timedelta(days=365)

        berth_dict = validated_data.pop('berth')
        berth = None

        if not berth_dict.get('id'):
            if berth_dict.get('type') != Berth.GROUND:
                raise serializers.ValidationError(_('Only ground type berths can be created with reservation'))
            if request_user.is_staff:
                berth = self.create_berth(berth_dict)
            else:
                ground_berth_price = 30.00
                try:
                    ground_berth_price = GroundBerthPrice.objects.latest('id').price
                except:
                    pass
                berth = self.create_berth({
                    "price": ground_berth_price,
                    "type":"ground",
                    "resource":{
                        "name":"Numeroimaton",
                        "name_fi":"Numeroimaton",
                        "unit": Unit.objects.get(name__icontains='poletti'),
                        "reservable": True
                    },
                    "length_cm":0,
                    "width_cm":0,
                    "depth_cm":0
                })

        reservation_data['resource'] = berth.resource
        reservation = Reservation.objects.create(**reservation_data)
        resource = reservation.resource
        resource.reservable = False
        resource.save()
        berthReservation = BerthReservation.objects.create(reservation=reservation, berth=berth, **validated_data)
        return berthReservation

    def create_berth(self, berth):
        resource_data = berth.pop('resource')

        if not berth.get('price'):
            ground_berth_price = 30.00
            try:
                ground_berth_price = GroundBerthPrice.objects.latest('id').price
            except:
                pass
            berth['price'] = ground_berth_price

        if not resource_data.get('unit_id') and not resource_data.get('unit'):
            resource_data['unit'] = Unit.objects.get(name__icontains='poletti')

        if not resource_data.get('type_id' and not resource_data.get('type')):
            resource_data['type'] = ResourceType.objects.get(main_type='berth')

        resource = Resource.objects.create(**resource_data)
        new_berth = Berth.objects.create(resource=resource, **berth)

        return new_berth

class PurchaseSerializer(TranslatedModelSerializer, munigeo_api.GeoModelSerializer):
    berth_reservation = BerthReservationSerializer(read_only=True)
    class Meta:
        model = Purchase
        fields = ['id', 'berth_reservation', 'purchase_code', 'reserver_name', 'reserver_email_address', 'reserver_phone_number', 'reserver_address_street', 'reserver_address_zip', 'reserver_address_city', 'vat_percent', 'price_vat', 'product_name', 'purchase_process_started', 'purchase_process_success', 'purchase_process_failure', 'purchase_process_notified']

class BerthReservationFilter(django_filters.FilterSet):
    unit_id = django_filters.CharFilter(name="reservation__resource__unit_id")
    begin = django_filters.DateTimeFromToRangeFilter(name="reservation__resource__begin")
    is_paid = django_filters.BooleanFilter(name="is_paid")
    class Meta:
        model = BerthReservation
        fields = ['unit_id', 'is_paid']

class BerthReservationFilterBackend(filters.BaseFilterBackend):
    """
    Filter reservations by time.
    """

    def filter_queryset(self, request, queryset, view):
        params = request.query_params
        times = {}
        filter_type = 'all'

        if not 'show_cancelled' in params:
            queryset = queryset.exclude(reservation__state='cancelled')

        if 'date_filter_type' in params:
            filter_type = params['date_filter_type'];

        for name in ('begin', 'end'):
            if name not in params:
                continue
            try:
                times[name] = arrow.get(params[name]).to('utc').datetime
            except ParserError:
                raise exceptions.ParseError("'%s' must be a timestamp in ISO 8601 format" % name)
        if filter_type == 'all':
            if times.get('begin', None):
                queryset = queryset.filter(reservation__end__gte=times['begin'])
            if times.get('end', None):
                queryset = queryset.filter(reservation__begin__lte=times['end'])
        elif filter_type == 'begin':
            if times.get('begin', None):
                queryset = queryset.filter(reservation__begin__gte=times['begin'])
            if times.get('end', None):
                queryset = queryset.filter(reservation__begin__lte=times['end'])
        elif filter_type == 'end':
            if times.get('begin', None):
                queryset = queryset.filter(reservation__end__gte=times['begin'])
            if times.get('end', None):
                queryset = queryset.filter(reservation__end__lte=times['end'])

        return queryset

class BerthReservationPagination(pagination.PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 5000
    def get_paginated_response(self, data):
        next_page = ''
        previous_page = ''
        if self.page.has_next():
            next_page = self.page.next_page_number()
        if self.page.has_previous():
            previous_page = self.page.previous_page_number()
        return Response({
            'next': next_page,
            'previous': previous_page,
            'count': self.page.paginator.count,
            'results': data
        })

class StaffWriteOnly(permissions.BasePermission):
     def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS or request.user.is_staff

class BerthReservationViewSet(munigeo_api.GeoModelAPIView, viewsets.ModelViewSet):
    queryset = BerthReservation.objects.all().select_related('reservation', 'reservation__user', 'reservation__resource', 'reservation__resource__unit')
    serializer_class = BerthReservationSerializer
    lookup_field = 'id'
    permission_classes = [StaffWriteOnly, permissions.IsAuthenticated]
    filter_class = BerthReservationFilter

    filter_backends = (DjangoFilterBackend,filters.SearchFilter,RelatedOrderingFilter,BerthReservationFilterBackend)
    filter_fields = ('reserver_ssn')
    search_fields = ['reserver_ssn', 'reservation__billing_address_street', 'reservation__reserver_email_address', 'reservation__reserver_name', 'reservation__reserver_phone_number']
    ordering_fields = ('__all__')
    pagination_class = BerthReservationPagination

    def get_serializer_class(self):
        if self.request.method == 'POST' and self.request.data.get('berth'):
            if self.request.data.get('berth').get('type') == Berth.GROUND and not self.request.data.get('berth').get('id'):
                return BerthReservationGroundBerthSerializer
            else:
                return BerthReservationSerializer
        return BerthReservationSerializer

    def perform_create(self, serializer):
        request = self.request
        if request.data.get('berth').get('type') != Berth.GROUND:
            code = request.data.pop('code')
            berth = Berth.objects.get(pk=request.data['berth']['id'], is_deleted=False)

            if code != hashlib.sha1(str(berth.reserving).encode('utf-8')).hexdigest():
                raise ValidationError(_('Invalid meta data'))
        berth_reservation = serializer.save()
        tasks.send_confirmation.delay(berth_reservation.pk)

class PurchaseView(APIView):
    permission_classes = (permissions.AllowAny,)
    def post(self, request, format=None):
        if request.user.is_authenticated():
            PermissionDenied(_('This API is only for non-authenticated users'))
        if not settings.PAYTRAIL_MERCHANT_ID or not settings.PAYTRAIL_MERCHANT_SECRET:
            raise ImproperlyConfigured(_('Paytrail credentials are incorrect or missing'))

        reservation = request.data['reservation']
        reservation['begin'] = timezone.now()
        reservation['end'] = timezone.now() + timedelta(days=365)
        request.data['reservation'] = reservation
        # unauthenticated user can not make reservations linked to user objects
        request.data['reservation'].pop('user', None)

        if request.data.get('berth').get('type') != Berth.GROUND:
            code = request.data.pop('code')
            berth = Berth.objects.get(pk=request.data['berth']['id'], is_deleted=False)

            if code != hashlib.sha1(str(berth.reserving).encode('utf-8')).hexdigest():
                raise ValidationError(_('Invalid meta data'))

            serializer = BerthReservationSerializer(data=request.data, context={'request': request})
        else:
            serializer = BerthReservationGroundBerthSerializer(data=request.data, context={'request': request})

        if serializer.is_valid():
            reservation = serializer.save()
            url = request.build_absolute_uri()
            purchase_code = hashlib.sha1(str(reservation.reservation.created_at).encode('utf-8') + str(reservation.pk).encode('utf-8')).hexdigest()

            contact = PaytrailContact(**reservation.get_payment_contact_data())
            product = PaytrailProduct(**reservation.get_payment_product_data())
            url_set = PaytrailUrlset(success_url=url + '?success=' + purchase_code, failure_url=url + '?failure=' + purchase_code, notification_url=url + '?notification=' + purchase_code)
            purchase = Purchase.objects.create(berth_reservation=reservation,
                    purchase_code=purchase_code,
                    reserver_name=reservation.reservation.reserver_name,
                    reserver_email_address=reservation.reservation.reserver_email_address,
                    reserver_phone_number=reservation.reservation.reserver_phone_number,
                    reserver_address_street=reservation.reservation.reserver_address_street,
                    reserver_address_zip=reservation.reservation.reserver_address_zip,
                    reserver_address_city=reservation.reservation.reserver_address_city,
                    vat_percent=product.get_data()['vat'],
                    price_vat=product.get_data()['price'],
                    product_name=product.get_data()['title']
                    )
            payment = PaytrailPaymentExtended(
                    service='VARAUS',
                    product='VENEPAIKKA',
                    product_type=product.get_data()['berth_type'],
                    order_number=purchase.pk,
                    contact=contact,
                    urlset=url_set
                    )
            payment.add_product(product)

            query_string = PaytrailArguments(
                merchant_auth_hash=settings.PAYTRAIL_MERCHANT_SECRET,
                merchant_id=settings.PAYTRAIL_MERCHANT_ID,
                url_success=url + '?success=' + purchase_code,
                url_cancel=url + '?failure=' + purchase_code,
                url_notify=url + '?notification=' + purchase_code,
                order_number=payment.get_data()['orderNumber'],
                params_in=(
                    'MERCHANT_ID,'
                    'URL_SUCCESS,'
                    'URL_CANCEL,'
                    'URL_NOTIFY,'
                    'ORDER_NUMBER,'
                    'PARAMS_IN,'
                    'PARAMS_OUT,'
                    'PAYMENT_METHODS,'
                    'ITEM_TITLE[0],'
                    'ITEM_ID[0],'
                    'ITEM_QUANTITY[0],'
                    'ITEM_UNIT_PRICE[0],'
                    'ITEM_VAT_PERCENT[0],'
                    'ITEM_DISCOUNT_PERCENT[0],'
                    'ITEM_TYPE[0],'
                    'PAYER_PERSON_PHONE,'
                    'PAYER_PERSON_EMAIL,'
                    'PAYER_PERSON_FIRSTNAME,'
                    'PAYER_PERSON_LASTNAME,'
                    'PAYER_PERSON_ADDR_STREET,'
                    'PAYER_PERSON_ADDR_POSTAL_CODE,'
                    'PAYER_PERSON_ADDR_TOWN'
                    ),
                params_out='PAYMENT_ID,TIMESTAMP,STATUS',
                payment_methods='1,2,3,5,6,10,50,51,52,61',
                item_title=product.get_data()['title'],
                item_id=product.get_data()['code'],
                item_quantity=product.get_data()['amount'],
                item_unit_price=product.get_data()['price'],
                item_vat_percent=product.get_data()['vat'],
                item_discount_percent=product.get_data()['discount'],
                item_type=product.get_data()['type'],
                payer_person_phone=contact.get_data()['mobile'],
                payer_person_email=contact.get_data()['email'],
                payer_person_firstname=contact.get_data()['firstName'],
                payer_parson_lastname=contact.get_data()['lastName'],
                payer_person_addr_street=contact.get_data()['address']['street'],
                payer_person_add_postal_code=contact.get_data()['address']['postalCode'],
                payer_person_addr_town=contact.get_data()['address']['postalOffice'],
            )

            return Response({'query_string': query_string.get_data()}, status=status.HTTP_200_OK)
        else:
            LOG.info(serializer.errors)
            raise ValidationError(_('Invalid payment data'))

    def get(self, request, format=None):
        if request.GET.get('success', None):
            if not settings.PAYTRAIL_MERCHANT_ID or not settings.PAYTRAIL_MERCHANT_SECRET:
                raise ImproperlyConfigured(_('Paytrail credentials are incorrect or missing'))
            client = PaytrailAPIClient(merchant_id=settings.PAYTRAIL_MERCHANT_ID, merchant_secret=settings.PAYTRAIL_MERCHANT_SECRET)
            if not client.validate_callback_data(request.GET):
                raise ValidationError(_('Checksum failed. Invalid payment.'))
            purchase_code = request.GET.get('success', None)
            purchase = Purchase.objects.get(purchase_code=purchase_code)
            purchase.payment_service_order_number = request.GET.get('ORDER_NUMBER', None)
            purchase.payment_service_timestamp = request.GET.get('TIMESTAMP', None)
            purchase.payment_service_paid = request.GET.get('PAID', None)
            purchase.payment_service_method = request.GET.get('METHOD', None)
            purchase.payment_service_return_authcode = request.GET.get('RETURN_AUTHCODE', None)
            purchase.save()
            purchase.set_success()
            return HttpResponseRedirect('/#purchase/' + purchase_code)
        elif request.GET.get('failure', None):
            if not settings.PAYTRAIL_MERCHANT_ID or not settings.PAYTRAIL_MERCHANT_SECRET:
                raise ImproperlyConfigured(_('Paytrail credentials are incorrect or missing'))
            client = PaytrailAPIClient(merchant_id=settings.PAYTRAIL_MERCHANT_ID, merchant_secret=settings.PAYTRAIL_MERCHANT_SECRET)
            if not client.validate_callback_data(request.GET):
                raise ValidationError(_('Checksum failed. Invalid payment.'))
            purchase_code = request.GET.get('failure', None)
            purchase = Purchase.objects.get(purchase_code=purchase_code)
            purchase.payment_service_order_number = request.GET.get('ORDER_NUMBER', None)
            purchase.payment_service_timestamp = request.GET.get('TIMESTAMP', None)
            purchase.payment_service_paid = request.GET.get('PAID', None)
            purchase.payment_service_method = request.GET.get('METHOD', None)
            purchase.payment_service_return_authcode = request.GET.get('RETURN_AUTHCODE', None)
            purchase.save()
            purchase.set_failure()
            purchase.berth_reservation.cancel_reservation(self.request.user)
            return HttpResponseRedirect('/#purchase/' + purchase_code)
        elif request.GET.get('notification', None):
            if not settings.PAYTRAIL_MERCHANT_ID or not settings.PAYTRAIL_MERCHANT_SECRET:
                raise ImproperlyConfigured(_('Paytrail credentials are incorrect or missing'))
            client = PaytrailAPIClient(merchant_id=settings.PAYTRAIL_MERCHANT_ID, merchant_secret=settings.PAYTRAIL_MERCHANT_SECRET)
            if not client.validate_callback_data(request.GET):
                raise ValidationError(_('Checksum failed. Invalid payment.'))
            purchase_code = request.GET.get('notification', None)
            purchase = Purchase.objects.get(purchase_code=purchase_code)
            purchase.berth_reservation.set_paid(True)
            purchase.set_notification()
            return Response({}, status=status.HTTP_200_OK)
        elif request.GET.get('code', None):
            if not settings.PAYTRAIL_MERCHANT_ID or not settings.PAYTRAIL_MERCHANT_SECRET:
                raise ImproperlyConfigured(_('Paytrail credentials are incorrect or missing'))
            client = PaytrailAPIClient(merchant_id=settings.PAYTRAIL_MERCHANT_ID, merchant_secret=settings.PAYTRAIL_MERCHANT_SECRET)
            purchase_code = request.GET.get('code', None)
            purchase = Purchase.objects.get(purchase_code=purchase_code)
            if purchase.report_is_seen():
                raise PermissionDenied(_('Youre not allowed to see this purchase'))
            serializer = PurchaseSerializer(purchase, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            if not request.user.is_authenticated() or not request.user.is_staff:
                raise PermissionDenied(_('This API is only for authenticated users'))

            if 'start' not in self.request.GET or 'end' not in self.request.GET:
                raise ParseError(_('Invalid parameters provided'))

            start = self.request.GET.get('start')
            end = self.request.GET.get('end')
            show_failed = self.request.GET.get('show_failed')
            if show_failed == 'true':
                show_failed = True
            else:
                show_failed = False

            purchases = Purchase.objects.filter(purchase_process_started__gte=start, purchase_process_started__lte=end)

            if not show_failed:
                purchases = purchases.exclude(purchase_process_success__isnull=True)

            purchases = purchases.order_by('-purchase_process_started')
            serializer = PurchaseSerializer(purchases, many=True, context={'request': request})

            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response({}, status=status.HTTP_404_NOT_FOUND)

    def patch(self, request, format=None):
        body_unicode = request.body.decode('utf-8')
        body = json.loads(body_unicode)
        if body.get('report_seen', None) and body.get('code', None):
            purchase_code = body.get('code', None)
            purchase = Purchase.objects.get(purchase_code=purchase_code)
            purchase.set_report_seen()
            return Response({}, status=status.HTTP_200_OK)

        if body.get('resource', None):
            time = timezone.now()
            berth = Berth.objects.get(resource_id=body.get('resource', None), is_deleted=False)
            if not berth.reserving or (time - berth.reserving).total_seconds() > 59 or berth.reserving_staff_member == request.user:
                berth.reserving = time
                if request.user and request.user.is_staff:
                    berth.reserving_staff_member = request.user
                else:
                    berth.reserving_staff_member = None
                berth.save()
            else:
                return Response(None, status=status.HTTP_404_NOT_FOUND)
            return Response({'code': hashlib.sha1(str(berth.reserving).encode('utf-8')).hexdigest()}, status=status.HTTP_200_OK)

        return Response(None, status=status.HTTP_404_NOT_FOUND)

class RenewalView(APIView):
    permission_classes = (permissions.AllowAny,)
    def post(self, request, format=None):
        if(request.data.get('code')):
            code = request.data.pop('code')

            if not code:
                raise ValidationError(_('Invalid renewal code'))

            old_berth_reservation_qs = BerthReservation.objects.filter(renewal_code=code, reservation__state=Reservation.CONFIRMED, reservation__end__gte=timezone.now()).exclude(child__reservation__state=Reservation.CONFIRMED).distinct()

            if len(old_berth_reservation_qs) != 1:
                raise ValidationError(_('Invalid reservation id'))

            old_berth_reservation = old_berth_reservation_qs.first()

            old_reservation = old_berth_reservation.reservation

            new_start = old_reservation.end
            new_end = new_start + timedelta(days=365)
            parent_id = old_berth_reservation.pk
            old_reservation.pk = None
            old_berth_reservation.pk = None
            new_reservation = old_reservation
            new_berth_reservation = old_berth_reservation

            new_reservation.begin = new_start
            new_reservation.end = new_end

            overlaps_existing = BerthReservation.objects.filter(reservation__begin__lt=new_end, reservation__end__gt=new_start, berth=new_berth_reservation.berth, reservation__state=Reservation.CONFIRMED).exists()
            if overlaps_existing:
                raise serializers.ValidationError(_('New reservation overlaps existing reservation'))

            if request.data.get('reserver_email_address'):
                new_reservation.reserver_email_address = request.data.get('reserver_email_address')
            if request.data.get('reserver_phone_number'):
                new_reservation.reserver_phone_number = request.data.get('reserver_phone_number')
            if request.data.get('reserver_address_street'):
                new_reservation.reserver_address_street = request.data.get('reserver_address_street')
            if request.data.get('reserver_address_zip'):
                new_reservation.reserver_address_zip = request.data.get('reserver_address_zip')
            if request.data.get('reserver_address_city'):
                new_reservation.reserver_address_city = request.data.get('reserver_address_city')

            new_reservation.save()

            new_berth_reservation.reservation = new_reservation
            new_berth_reservation.parent_id = parent_id
            new_berth_reservation.renewal_notification_day_sent_at = None
            new_berth_reservation.renewal_notification_week_sent_at = None
            new_berth_reservation.renewal_notification_month_sent_at = None
            new_berth_reservation.is_paid_at = None
            new_berth_reservation.is_paid = False
            new_berth_reservation.renewal_code = None
            new_berth_reservation.end_notification_sent_at = None
            new_berth_reservation.key_return_notification_sent_at = None
            new_berth_reservation.save()
            location = '//%s' % '/api/purchase/'
            url = request.build_absolute_uri(location)
            purchase_code = hashlib.sha1(str(new_berth_reservation.reservation.created_at).encode('utf-8') + str(new_berth_reservation.pk).encode('utf-8')).hexdigest()

            contact = PaytrailContact(**new_berth_reservation.get_payment_contact_data())
            product = PaytrailProduct(**new_berth_reservation.get_payment_product_data())
            url_set = PaytrailUrlset(success_url=url + '?success=' + purchase_code, failure_url=url + '?failure=' + purchase_code, notification_url=url + '?notification=' + purchase_code)
            purchase = Purchase.objects.create(berth_reservation=new_berth_reservation,
                    purchase_code=purchase_code,
                    reserver_name=new_berth_reservation.reservation.reserver_name,
                    reserver_email_address=new_berth_reservation.reservation.reserver_email_address,
                    reserver_phone_number=new_berth_reservation.reservation.reserver_phone_number,
                    reserver_address_street=new_berth_reservation.reservation.reserver_address_street,
                    reserver_address_zip=new_berth_reservation.reservation.reserver_address_zip,
                    reserver_address_city=new_berth_reservation.reservation.reserver_address_city,
                    vat_percent=product.get_data()['vat'],
                    price_vat=product.get_data()['price'],
                    product_name=product.get_data()['title'])
            payment = PaytrailPaymentExtended(
                        service='VARAUS',
                        product='VENEPAIKKA',
                        product_type=product.get_data()['berth_type'],
                        order_number=purchase.pk,
                        contact=contact,
                        urlset=url_set
                        )
            payment.add_product(product)
            query_string = PaytrailArguments(
                merchant_auth_hash=settings.PAYTRAIL_MERCHANT_SECRET,
                merchant_id=settings.PAYTRAIL_MERCHANT_ID,
                url_success=url + '?success=' + purchase_code,
                url_cancel=url + '?failure=' + purchase_code,
                url_notify=url + '?notification=' + purchase_code,
                order_number=payment.get_data()['orderNumber'],
                params_in=(
                    'MERCHANT_ID,'
                    'URL_SUCCESS,'
                    'URL_CANCEL,'
                    'URL_NOTIFY,'
                    'ORDER_NUMBER,'
                    'PARAMS_IN,'
                    'PARAMS_OUT,'
                    'PAYMENT_METHODS,'
                    'ITEM_TITLE[0],'
                    'ITEM_ID[0],'
                    'ITEM_QUANTITY[0],'
                    'ITEM_UNIT_PRICE[0],'
                    'ITEM_VAT_PERCENT[0],'
                    'ITEM_DISCOUNT_PERCENT[0],'
                    'ITEM_TYPE[0],'
                    'PAYER_PERSON_PHONE,'
                    'PAYER_PERSON_EMAIL,'
                    'PAYER_PERSON_FIRSTNAME,'
                    'PAYER_PERSON_LASTNAME,'
                    'PAYER_PERSON_ADDR_STREET,'
                    'PAYER_PERSON_ADDR_POSTAL_CODE,'
                    'PAYER_PERSON_ADDR_TOWN'
                    ),
                params_out='PAYMENT_ID,TIMESTAMP,STATUS',
                payment_methods='1,2,3,5,6,10,50,51,52,61',
                item_title=product.get_data()['title'],
                item_id=product.get_data()['code'],
                item_quantity=product.get_data()['amount'],
                item_unit_price=product.get_data()['price'],
                item_vat_percent=product.get_data()['vat'],
                item_discount_percent=product.get_data()['discount'],
                item_type=product.get_data()['type'],
                payer_person_phone=contact.get_data()['mobile'],
                payer_person_email=contact.get_data()['email'],
                payer_person_firstname=contact.get_data()['firstName'],
                payer_parson_lastname=contact.get_data()['lastName'],
                payer_person_addr_street=contact.get_data()['address']['street'],
                payer_person_add_postal_code=contact.get_data()['address']['postalCode'],
                payer_person_addr_town=contact.get_data()['address']['postalOffice'],
            )

            return Response({'query_string': query_string.get_data()}, status=status.HTTP_200_OK)
        elif request.data.get('reservation_id'):
            if not request.user.is_authenticated() or not request.user.is_staff:
                raise PermissionDenied(_('This API is only for authenticated users'))

            old_berth_reservation_qs = BerthReservation.objects.filter(pk=request.data.get('reservation_id'), reservation__state=Reservation.CONFIRMED, reservation__end__gte=timezone.now()).exclude(child__reservation__state=Reservation.CONFIRMED).distinct()

            if len(old_berth_reservation_qs) != 1:
                raise ValidationError(_('Invalid reservation id'))

            old_berth_reservation = old_berth_reservation_qs.first()

            old_reservation = old_berth_reservation.reservation

            new_start = old_reservation.end
            new_end = new_start + timedelta(days=365)
            parent_id = old_berth_reservation.pk
            old_reservation.pk = None
            old_berth_reservation.pk = None
            new_reservation = old_reservation
            new_berth_reservation = old_berth_reservation

            new_reservation.begin = new_start
            new_reservation.end = new_end

            overlaps_existing = BerthReservation.objects.filter(reservation__begin__lt=new_end, reservation__end__gt=new_start, berth=new_berth_reservation.berth, reservation__state=Reservation.CONFIRMED).exists()
            if overlaps_existing:
                raise serializers.ValidationError(_('New reservation overlaps existing reservation'))

            if request.data.get('reserver_email_address'):
                new_reservation.reserver_email_address = request.data.get('reserver_email_address')
            if request.data.get('reserver_phone_number'):
                new_reservation.reserver_phone_number = request.data.get('reserver_phone_number')
            if request.data.get('reserver_address_street'):
                new_reservation.reserver_address_street = request.data.get('reserver_address_street')
            if request.data.get('reserver_address_zip'):
                new_reservation.reserver_address_zip = request.data.get('reserver_address_zip')
            if request.data.get('reserver_address_city'):
                new_reservation.reserver_address_city = request.data.get('reserver_address_city')

            new_reservation.save()

            new_berth_reservation.reservation = new_reservation
            new_berth_reservation.parent_id = parent_id
            new_berth_reservation.renewal_notification_day_sent_at = None
            new_berth_reservation.renewal_notification_week_sent_at = None
            new_berth_reservation.renewal_notification_month_sent_at = None
            new_berth_reservation.is_paid_at = None
            new_berth_reservation.is_paid = False
            new_berth_reservation.renewal_code = None
            new_berth_reservation.end_notification_sent_at = None
            new_berth_reservation.key_return_notification_sent_at = None

            new_berth_reservation.save()

            serializer = BerthReservationSerializer(new_berth_reservation, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)

    def get(self, request, format=None):
        if request.GET.get('code', None):
            code = request.GET.get('code', None)
            reservation_qs = BerthReservation.objects.filter(reservation__state=Reservation.CONFIRMED, renewal_code=code).exclude(child__reservation__state=Reservation.CONFIRMED).distinct()
            if len(reservation_qs) != 1:
                raise ValidationError(_('Invalid renewal code'))

            reservation = reservation_qs.first()
            if reservation.reservation.end < timezone.now():
                return Response(None, status=status.HTTP_404_NOT_FOUND)
            serializer = BerthReservationSerializer(reservation, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(None, status=status.HTTP_404_NOT_FOUND)

class SmsView(APIView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request, format=None):
        if request.data.get('AccountSid') != settings.TWILIO_ACCOUNT_SID:
            raise PermissionDenied(_('Authentication failed'))

        if request.data.get('SmsStatus') == 'delivered':
            sms = SMSMessage.objects.get(twilio_id=request.data.get('SmsSid'))
            sms.success = True
            sms.save()

        return Response(status=status.HTTP_204_NO_CONTENT)


register_view(BerthReservationViewSet, 'berth_reservation')
