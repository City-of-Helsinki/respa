import arrow
import django_filters
from arrow.parser import ParserError
from django.core.exceptions import PermissionDenied
from rest_framework import viewsets, serializers, filters, exceptions, permissions, status, pagination
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from munigeo import api as munigeo_api
from resources.models import Reservation, Resource, Unit
from hmlvaraus.api.resource import ResourceSerializer
from hmlvaraus.models.berth import Berth
from hmlvaraus.models.hml_reservation import HMLReservation
from resources.api.base import TranslatedModelSerializer, register_view
from hmlvaraus.utils.utils import RelatedOrderingFilter
from django.utils.translation import ugettext_lazy as _

class BerthSerializer(TranslatedModelSerializer, munigeo_api.GeoModelSerializer):
    resource = ResourceSerializer(required=True)
    width_cm = serializers.IntegerField(required=True)
    depth_cm = serializers.IntegerField(required=True)
    length_cm = serializers.IntegerField(required=True)
    type = serializers.CharField(required=True)
    partial = True

    class Meta:
        model = Berth
        fields = ['id', 'width_cm', 'length_cm', 'depth_cm', 'resource', 'type', 'is_disabled', 'price']

    def create(self, validated_data):
        resource_data = validated_data.pop('resource')
        resource = Resource.objects.create(**resource_data)
        berth = Berth.objects.create(resource=resource, **validated_data)
        return berth

    def update(self, instance, validated_data):
        resource_data = validated_data.pop('resource')

        resource = instance.resource

        instance.width_cm = validated_data.get('width_cm', instance.width_cm)
        instance.depth_cm = validated_data.get('depth_cm', instance.depth_cm)
        instance.length_cm = validated_data.get('length_cm', instance.length_cm)
        instance.price = validated_data.get('price', instance.price)
        instance.is_disabled = validated_data.get('is_disabled', instance.is_disabled)
        instance.type = validated_data.get('type', instance.type)
        instance.save()

        new_resource_name = resource_data.get('name')

        resource.name_fi = new_resource_name.get('fi', resource.name_fi)
        resource.name = new_resource_name.get('fi', resource.name_fi)

        new_resource_description = resource_data.get('description')

        resource.description_fi = new_resource_description.get('fi', resource.description_fi)
        resource.description = new_resource_description.get('fi', resource.description_fi)

        resource.unit = resource_data.get('unit', resource.unit)
        resource.save()

        return instance

    def to_representation(self, instance):
        data = super(BerthSerializer, self).to_representation(instance)
        return data;

    def validate(self, data):
        request_user = self.context['request'].user
        return data

    def validate_price(self, value):
        if not self.is_number(value) and value < 0:
            raise serializers.ValidationError(_('Value out of bounds'))
        return value

    def validate_width_cm(self, value):
        if value < 0 or value > 1000:
            raise serializers.ValidationError(_('Value out of bounds'))
        return value

    def validate_height_cm(self, value):
        if value < 0 or value > 1000:
            raise serializers.ValidationError(_('Value out of bounds'))
        return value

    def validate_depth_cm(self, value):
        if value < 0 or value > 1000:
            raise serializers.ValidationError(_('Value out of bounds'))
        return value

    def validate_type(self, value):
        if value not in ['number', 'ground', 'dock']:
            raise serializers.ValidationError(_('Value out of bounds'))
        return value

    def is_number(self, value):
        try:
            float(value)
            return True
        except ValueError:
            return False

class BerthFilter(django_filters.FilterSet):
    max_width = django_filters.NumberFilter(name="width_cm", lookup_expr='lte')
    min_width = django_filters.NumberFilter(name="width_cm", lookup_expr='gte')

    max_length = django_filters.NumberFilter(name="length_cm", lookup_expr='lte')
    min_length = django_filters.NumberFilter(name="length_cm", lookup_expr='gte')

    max_depth = django_filters.NumberFilter(name="depth_cm", lookup_expr='lte')
    min_depth = django_filters.NumberFilter(name="depth_cm", lookup_expr='gte')

    max_price = django_filters.NumberFilter(name="price", lookup_expr='lte')
    min_price = django_filters.NumberFilter(name="price", lookup_expr='gte')

    unit_id = django_filters.CharFilter(name="resource__unit_id")

    class Meta:
        model = Berth
        fields = ['max_width', 'min_width', 'max_length', 'min_length', 'max_depth', 'min_depth', 'max_price', 'min_price', 'unit_id', 'type']

class BerthFilterBackend(filters.BaseFilterBackend):
    """
    Filter reservations by time.
    """

    def filter_queryset(self, request, queryset, view):
        params = request.query_params
        times = {}
        filter_type = '';
        if 'date_filter_type' in params:
            filter_type = params['date_filter_type'];

        if 'hide_disabled' in params:
            queryset = queryset.exclude(is_disabled=True)

        for name in ('berth_begin', 'berth_end'):
            if name not in params:
                continue
            try:
                times[name] = arrow.get(params[name]).to('utc').datetime
            except ParserError:
                raise exceptions.ParseError("'%s' must be a timestamp in ISO 8601 format" % name)

        resources = []
        if not filter_type or filter_type == '':
            return queryset

        if times.get('berth_begin', None) and times.get('berth_end', None):
            resources = HMLReservation.objects.filter(reservation__end__gte=times['berth_begin'], reservation__begin__lte=times['berth_end'], reservation__state='confirmed').values_list('reservation__resource_id', flat=True)
        elif times.get('berth_begin', None):
            resources = HMLReservation.objects.filter(reservation__end__gte=times['berth_begin'], reservation__state='confirmed').values_list('reservation__resource_id', flat=True)
        elif times.get('berth_end', None):
            resources = HMLReservation.objects.filter(reservation__begin__lte=times['berth_end'], reservation__state='confirmed').values_list('reservation__resource_id', flat=True)

        if not filter_type or filter_type == 'not_reserved':
            queryset = queryset.exclude(resource__id__in = resources)
        elif filter_type == 'reserved':
            queryset = queryset.filter(resource__id__in = resources)

        return queryset

class BerthPagination(pagination.PageNumberPagination):
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

class BerthViewSet(munigeo_api.GeoModelAPIView, viewsets.ModelViewSet):
    queryset = Berth.objects.all().select_related('resource', 'resource__unit').prefetch_related('resource', 'resource__unit')
    serializer_class = BerthSerializer
    lookup_field = 'id'

    filter_class = BerthFilter
    permission_classes = [StaffWriteOnly]
    filter_backends = (DjangoFilterBackend,filters.SearchFilter,RelatedOrderingFilter, BerthFilterBackend)
    filter_fields = ['type']
    search_fields = ['type', 'resource__name', 'resource__name_fi', 'resource__unit__name', 'resource__unit__name_fi', 'hml_reservations__reservation__reserver_name', 'hml_reservations__reservation__reserver_email_address', 'hml_reservations__reservation__reserver_phone_number']
    ordering_fields = ('__all__')
    pagination_class = BerthPagination

    def destroy(self, request, *args, **kwargs):
        try:
            berth = self.get_object();
            resource_id = berth.resource.id
            resource = Resource.objects.get(pk=resource_id).delete()
            try:
                Reservation.objects.get(resource=resource).delete()
            except:
                pass
            berth.delete()
        except:
            return Response(status=status.HTTP_404_NOT_FOUND, data=_('Boat resource cannot be found'))

        return Response(status=status.HTTP_204_NO_CONTENT, data=_('Boat resource successfully created'))


register_view(BerthViewSet, 'berth')
