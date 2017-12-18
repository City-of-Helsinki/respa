import arrow
import django_filters
import re
from arrow.parser import ParserError
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from rest_framework import viewsets, serializers, filters, exceptions, permissions, pagination
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from munigeo import api as munigeo_api
from resources.models import Reservation
from hmlvaraus.api.reservation import ReservationSerializer
from hmlvaraus.api.berth import BerthSerializer
from hmlvaraus.models.hml_reservation import HMLReservation
from resources.api.base import TranslatedModelSerializer, register_view
from hmlvaraus.utils.utils import RelatedOrderingFilter
from django.utils.translation import ugettext_lazy as _
from hmlvaraus.models.berth import Berth
from resources.models.resource import Resource

class HMLReservationSerializer(TranslatedModelSerializer, munigeo_api.GeoModelSerializer):
    reservation = ReservationSerializer(required=True)
    is_paid = serializers.BooleanField(required=False)
    reserver_ssn = serializers.CharField(required=False)
    berth = BerthSerializer(required=True)
    partial = True

    class Meta:
        model = HMLReservation
        fields = ['id', 'berth', 'is_paid', 'reserver_ssn', 'reservation', 'state_updated_at', 'is_paid_at', 'key_returned', 'key_returned_at']

    def validate(self, data):
        request_user = self.context['request'].user

        if self.context['request'].method == 'POST' and Reservation.objects.filter(resource__id=data['reservation']['resource'].id, state=Reservation.CONFIRMED).exists():
            raise serializers.ValidationError(_('Resource is already reserved and scheduled for renewal'))

        return data

    def create(self, validated_data):
        reservation_data = validated_data.pop('reservation')
        reservation = Reservation.objects.create(**reservation_data)
        resource = Resource.objects.get(id=reservation_data['resource'].id)
        resource.reservable = False
        resource.save()
        berth_data = validated_data.pop('berth')
        berth = Berth.objects.get(pk=resource.berth.pk)
        hmlReservation = HMLReservation.objects.create(reservation=reservation, berth=berth, **validated_data)
        return hmlReservation

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
        reservation.save()

        return instance

    def update_reservation_status(self, instance, validated_data):
        is_paid = validated_data.get('is_paid')
        if is_paid != None:
            if is_paid:
                instance.is_paid_at = timezone.now()
                instance.is_paid = True
            else:
                instance.is_paid_at = None
                instance.is_paid = False
        key_returned = validated_data.get('key_returned')
        if key_returned != None:
            if key_returned:
                resource = instance.reservation.resource
                resource.reservable = True
                resource.save()
                instance.key_returned_at = timezone.now()
                instance.key_returned = True
            else:
                instance.key_returned_at = None
                instance.key_returned = False

        instance.save()

        return instance

    def to_representation(self, instance):
        data = super(HMLReservationSerializer, self).to_representation(instance)
        return data;

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

class HMLReservationFilter(django_filters.FilterSet):
    unit_id = django_filters.CharFilter(name="reservation__resource__unit_id")
    begin = django_filters.DateTimeFromToRangeFilter(name="reservation__resource__begin")
    is_paid = django_filters.BooleanFilter(name="is_paid")
    class Meta:
        model = HMLReservation
        fields = ['unit_id', 'is_paid']

class HMLReservationFilterBackend(filters.BaseFilterBackend):
    """
    Filter reservations by time.
    """

    def filter_queryset(self, request, queryset, view):
        params = request.query_params
        times = {}
        filter_type = 'all';

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

class HMLReservationPagination(pagination.PageNumberPagination):
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

class HMLReservationViewSet(munigeo_api.GeoModelAPIView, viewsets.ModelViewSet):
    queryset = HMLReservation.objects.all().select_related('reservation', 'reservation__user', 'reservation__resource', 'reservation__resource__unit')
    serializer_class = HMLReservationSerializer
    lookup_field = 'id'
    permission_classes = [StaffWriteOnly]
    filter_class = HMLReservationFilter

    filter_backends = (DjangoFilterBackend,filters.SearchFilter,RelatedOrderingFilter,HMLReservationFilterBackend)
    filter_fields = ('reserver_ssn')
    search_fields = ['reserver_ssn', 'reservation__billing_address_street', 'reservation__reserver_email_address', 'reservation__reserver_name', 'reservation__reserver_phone_number']
    ordering_fields = ('__all__')
    pagination_class = HMLReservationPagination

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        data = self.request._data
        if 'state' in data:
            id = int(self.kwargs.get('id'))
            hml_reservation = HMLReservation.objects.get(pk=id)
            reservation = hml_reservation.reservation
            reservation.set_state(data['state'], self.request.user)
            hml_reservation.state_updated_at = timezone.now()
            hml_reservation.save()
        return serializer.save()

register_view(HMLReservationViewSet, 'hml_reservation')
