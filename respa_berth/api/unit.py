import django_filters
import json
from django.core.exceptions import PermissionDenied
from rest_framework import viewsets, serializers, filters, permissions, pagination, status
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from munigeo import api as munigeo_api
from resources.models import Resource, Unit, UnitIdentifier, Reservation
from respa_berth.models.berth import Berth
from respa_berth.models.berth_reservation import BerthReservation
from resources.api.unit import UnitSerializer
from django.contrib.gis.geos import GEOSGeometry
from resources.api.base import register_view
from respa_berth.utils.utils import RelatedOrderingFilter
from resources.api.base import TranslatedModelSerializer
from django.utils import timezone
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _


BERTH_UNIT_IDENTIFIER = 'berth_reservation'


class SimpleResourceSerializer(TranslatedModelSerializer):
    name = serializers.StringRelatedField(many=True)

    class Meta:
        model = Resource
        fields = ['name', 'reservable']

class UnitSerializer(UnitSerializer):
    name = serializers.CharField(required=True)
    resources = SimpleResourceSerializer(read_only=True, many=True)
    resources_count = serializers.SerializerMethodField()
    resources_reservable_count = serializers.SerializerMethodField()
    reservation_count = serializers.SerializerMethodField()
    is_deleted = serializers.SerializerMethodField()

    def get_is_deleted(self, obj):
        return obj.resources.filter(berth__isnull=False).exclude(Q(berth__is_deleted=True)).count() == 0 and obj.resources.count() > 0

    def get_resources_count(self, obj):
        return obj.resources.filter(berth__isnull=False).exclude(Q(berth__is_deleted=True)).count()

    def get_resources_reservable_count(self, obj):
        return obj.resources.filter(berth__isnull=False).filter(reservable=True).exclude(Q(berth__type=Berth.GROUND) | Q(berth__is_disabled=True) | Q(berth__is_deleted=True)).count()

    def get_reservation_count(self, obj):
        return BerthReservation.objects.filter(berth__resource__in=obj.resources.all(), reservation__begin__lte=timezone.now(), reservation__end__gte=timezone.now(), reservation__state=Reservation.CONFIRMED).count()

    def validate(self, data):
        request_user = self.context['request'].user

        # if not request_user.is_staff:
        #     raise PermissionDenied()

        return data

    def to_internal_value(self, data):
        try:
            location = GEOSGeometry(json.dumps(data.get('location')))
        except:
            location = None
            pass

        return {
            'name': data.get('name', {}).get('fi', None),
            'name_fi': data.get('name', {}).get('fi', None),
            'street_address': data.get('street_address', {}).get('fi', None),
            'street_address_fi': data.get('street_address', {}).get('fi', None),
            'location': location,
            'address_zip': data.get('address_zip', None),
            'phone': data.get('phone', None),
            'email': data.get('email', None),
            'description': data.get('description', {}).get('fi', None),
            'description_fi': data.get('description', {}).get('fi', None),
        }

class UnitFilter(django_filters.FilterSet):
    class Meta:
        model = Unit
        fields = []

class UnitPagination(pagination.PageNumberPagination):
    page_size = 100
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

class UnitViewSet(munigeo_api.GeoModelAPIView, viewsets.ModelViewSet):
    queryset = Unit.objects.filter(identifiers__namespace=BERTH_UNIT_IDENTIFIER).prefetch_related('resources')
    serializer_class = UnitSerializer
    permission_classes = [StaffWriteOnly]
    filter_class = UnitFilter
    pagination_class = UnitPagination

    filter_backends = (DjangoFilterBackend,filters.SearchFilter,RelatedOrderingFilter)
    ordering_fields = ('__all__')
    search_fields = ['name', 'name_fi', 'street_address', 'email', 'description', 'phone']

    def perform_create(self, serializer):
        instance = serializer.save()
        UnitIdentifier.objects.create(unit=instance, namespace=BERTH_UNIT_IDENTIFIER, value=instance.pk)

    def destroy(self, request, *args, **kwargs):
        unit = self.get_object()
        berths = Berth.objects.filter(resource__unit=unit)
        Reservation.objects.filter(~Q(state=Reservation.CANCELLED), berth_reservation__berth__in=berths).update(state=Reservation.CANCELLED)
        berths.update(is_deleted=True)

        return Response(status=status.HTTP_204_NO_CONTENT, data=_('Unit successfully deleted'))

register_view(UnitViewSet, 'unit')
