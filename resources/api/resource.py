import collections
import datetime

import arrow
import django_filters
import pytz
from arrow.parser import ParserError

from django import forms
from django.db.models import Q
from django.core.urlresolvers import reverse
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from resources.pagination import PurposePagination
from rest_framework import exceptions, filters, mixins, serializers, viewsets, response, status
from rest_framework.decorators import detail_route
from rest_framework.exceptions import PermissionDenied
from rest_framework.fields import BooleanField

from munigeo import api as munigeo_api
from resources.models import (Purpose, Resource, ResourceImage, ResourceType, ResourceEquipment, TermsOfUse)
from .base import TranslatedModelSerializer, register_view
from .reservation import ReservationSerializer
from .unit import UnitSerializer
from .equipment import EquipmentSerializer


class PurposeSerializer(TranslatedModelSerializer):

    class Meta:
        model = Purpose
        fields = ['name', 'parent', 'id']


class PurposeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Purpose.objects.all()
    serializer_class = PurposeSerializer
    pagination_class = PurposePagination

    def get_queryset(self):
        if self.request.user.is_staff:
            return self.queryset
        else:
            return self.queryset.filter(public=True)

register_view(PurposeViewSet, 'purpose')


class ResourceTypeSerializer(TranslatedModelSerializer):

    class Meta:
        model = ResourceType
        fields = ['name', 'main_type', 'id']


class ResourceTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ResourceType.objects.all()
    serializer_class = ResourceTypeSerializer

register_view(ResourceTypeViewSet, 'type')


class NestedResourceImageSerializer(TranslatedModelSerializer):
    url = serializers.SerializerMethodField()

    def get_url(self, obj):
        url = reverse('resource-image-view', kwargs={'pk': obj.pk})
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(url)

    class Meta:
        model = ResourceImage
        fields = ('url', 'type', 'caption')
        ordering = ('resource', 'sort_order')


class ResourceEquipmentSerializer(TranslatedModelSerializer):

    class Meta:
        model = ResourceEquipment
        fields = ('equipment', 'data', 'id', 'description')
    equipment = EquipmentSerializer()

    def to_representation(self, obj):
        # remove unnecessary nesting and aliases
        ret = super().to_representation(obj)
        ret['name'] = ret['equipment']['name']
        ret['id'] = ret['equipment']['id']
        del ret['equipment']
        return ret


class TermsOfUseSerializer(TranslatedModelSerializer):
    class Meta:
        model = TermsOfUse
        fields = ('text',)


class ResourceSerializer(TranslatedModelSerializer, munigeo_api.GeoModelSerializer):
    purposes = PurposeSerializer(many=True)
    images = NestedResourceImageSerializer(many=True)
    equipment = ResourceEquipmentSerializer(many=True, read_only=True, source='resource_equipment')
    type = ResourceTypeSerializer()
    # FIXME: location field gets removed by munigeo
    location = serializers.SerializerMethodField()
    available_hours = serializers.SerializerMethodField()
    opening_hours = serializers.SerializerMethodField()
    reservations = serializers.SerializerMethodField()
    user_permissions = serializers.SerializerMethodField()
    supported_reservation_extra_fields = serializers.ReadOnlyField(source='get_supported_reservation_extra_field_names')
    required_reservation_extra_fields = serializers.ReadOnlyField(source='get_required_reservation_extra_field_names')
    is_favorite = serializers.SerializerMethodField()
    generic_terms = serializers.SerializerMethodField()
    reservable_days_in_advance = serializers.ReadOnlyField(source='get_reservable_days_in_advance')
    reservable_before = serializers.SerializerMethodField()

    def get_user_permissions(self, obj):
        request = self.context.get('request', None)
        return {
            'can_make_reservations': obj.can_make_reservations(request.user) if request else False,
            'is_admin': obj.is_admin(request.user) if request else False,
        }

    def get_is_favorite(self, obj):
        request = self.context.get('request', None)
        return request.user in obj.favorited_by.all()

    def get_generic_terms(self, obj):
        data = TermsOfUseSerializer(obj.generic_terms).data
        return data['text']

    def get_reservable_before(self, obj):
        request = self.context.get('request')
        user = request.user if request else None

        if user and obj.is_admin(user):
            return None
        else:
            return obj.get_reservable_before()

    def to_representation(self, obj):
        # we must parse the time parameters before serializing
        self.parse_parameters()
        if isinstance(obj, dict):
            # resource is already serialized
            return obj
        ret = super().to_representation(obj)
        if hasattr(obj, 'distance'):
            if obj.distance is not None:
                ret['distance'] = int(obj.distance.m)
            elif obj.unit_distance is not None:
                ret['distance'] = int(obj.unit_distance.m)

        return ret

    def get_location(self, obj):
        if obj.location is not None:
            return obj.location
        return obj.unit.location

    def parse_parameters(self):
        """
        Parses request time parameters for serializing available_hours, opening_hours
        and reservations
        """

        params = self.context['request'].query_params
        times = {}
        for name in ('start', 'end'):
            if name not in params:
                continue
            try:
                times[name] = arrow.get(params[name]).to('utc').datetime
            except ParserError:
                raise exceptions.ParseError("'%s' must be a timestamp in ISO 8601 format" % name)

        if 'duration' in params:
            times['duration'] = params['duration']

        if 'during_closing' in params:
            during_closing = params['during_closing'].lower()
            if during_closing == 'true' or during_closing == 'yes' or during_closing == '1':
                times['during_closing'] = True

        if len(times):
            if len(times) < 2:
                raise exceptions.ParseError("You must supply both 'start' and 'end'")
            self.context.update(times)

    def get_opening_hours(self, obj):
        if 'start' in self.context:
            start = self.context['start']
            end = self.context['end']
        else:
            start = None
            end = None

        hours_by_date = obj.get_opening_hours(start, end)

        ret = []
        for x in sorted(hours_by_date.items()):
            d = collections.OrderedDict(date=x[0].isoformat())
            if len(x[1]):
                d.update(x[1][0])
            ret.append(d)
        return ret

    def get_reservations(self, obj):
        if 'start' not in self.context:
            return None

        start = self.context['start']
        end = self.context['end']
        res_list = obj.reservations.all().filter(begin__lte=end)\
            .filter(end__gte=start).order_by('begin')
        res_ser_list = ReservationSerializer(res_list, many=True, context=self.context).data
        return res_ser_list

    def get_available_hours(self, obj):
        """
        The input datetimes must be converted to UTC before passing them to the model. Also, missing
        parameters have to be replaced with the start and end of today, as defined in the unit timezone.
        The returned UTC times are serialized in the unit timezone.
        """

        if 'start' not in self.context:
            return None
        zone = pytz.timezone(obj.unit.time_zone)

        try:
            duration = datetime.timedelta(minutes=int(self.context['duration']))
        except KeyError:
            duration = None

        try:
            during_closing = self.context['during_closing']
        except KeyError:
            during_closing = False

        hour_list = obj.get_available_hours(start=self.context['start'],
                                            end=self.context['end'],
                                            duration=duration,
                                            during_closing=during_closing)
        # the hours must be localized when serializing
        for hours in hour_list:
            hours['starts'] = hours['starts'].astimezone(zone)
            hours['ends'] = hours['ends'].astimezone(zone)
        return hour_list

    class Meta:
        model = Resource
        exclude = ('reservation_confirmed_notification_extra', 'access_code_type', 'reservation_metadata_set')


class ResourceDetailsSerializer(ResourceSerializer):
    unit = UnitSerializer()


class ParentFilter(django_filters.Filter):
    """
    Filter that also checks the parent field
    """

    def filter(self, qs, value):
        child_matches = super().filter(qs, value)
        self.name = self.name.replace('__id', '__parent__id')
        parent_matches = super().filter(qs, value)
        return child_matches | parent_matches


class ParentCharFilter(ParentFilter):
    field_class = forms.CharField


class DRFFilterBooleanWidget(django_filters.widgets.BooleanWidget):
    def render(self, *args, **kwargs):
        return None


class ResourceFilterSet(django_filters.FilterSet):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)

    purpose = ParentCharFilter(name='purposes__id', lookup_expr='iexact')
    type = django_filters.Filter(name='type__id', lookup_expr='in', widget=django_filters.widgets.CSVWidget)
    people = django_filters.NumberFilter(name='people_capacity', lookup_expr='gte')
    need_manual_confirmation = django_filters.BooleanFilter(name='need_manual_confirmation', widget=DRFFilterBooleanWidget)
    is_favorite = django_filters.BooleanFilter(method='filter_is_favorite', widget=DRFFilterBooleanWidget)
    unit = django_filters.CharFilter(name='unit__id', lookup_expr='iexact')
    group = django_filters.Filter(name='groups__identifier', lookup_expr='in', widget=django_filters.widgets.CSVWidget)
    equipment = django_filters.Filter(name='resource_equipment__equipment__id', lookup_expr='in',
                                      widget=django_filters.widgets.CSVWidget)

    def filter_is_favorite(self, queryset, name, value):
        if not self.user.is_authenticated():
            if value:
                return queryset.none()
            else:
                return queryset

        if value:
            return queryset.filter(favorited_by=self.user)
        else:
            return queryset.exclude(favorited_by=self.user)

    class Meta:
        model = Resource
        fields = ['purpose', 'type', 'people', 'need_manual_confirmation', 'is_favorite', 'unit']


class ResourceFilterBackend(filters.BaseFilterBackend):
    """
    Make request user available in the filter set.
    """
    def filter_queryset(self, request, queryset, view):
        return ResourceFilterSet(request.query_params, queryset=queryset, user=request.user).qs


class AvailableFilterBackend(filters.BaseFilterBackend):
    """
    Filters resource availability based on request parameters, serializing the queryset
    in the process. Therefore, AvailableFilterBackend must always be the final filter.
    """

    def filter_queryset(self, request, queryset, view):
        params = request.query_params
        # filtering is only done if all three parameters are provided
        if 'start' in params and 'end' in params and 'duration' in params:
            context = {'request': request}
            serializer = view.serializer_class(context=context)
            serialized_queryset = []
            for resource in queryset:
                serialized_resource = serializer.to_representation(resource)
                if serialized_resource['available_hours'] and serialized_resource['opening_hours']:
                    serialized_queryset.append(serialized_resource)
            return serialized_queryset
        return queryset


class LocationFilterBackend(filters.BaseFilterBackend):
    """
    Filters based on resource (or resource unit) location.
    """

    def filter_queryset(self, request, queryset, view):
        query_params = request.query_params
        if 'lat' not in query_params and 'lon' not in query_params:
            return queryset

        try:
            lat = float(query_params['lat'])
            lon = float(query_params['lon'])
        except ValueError:
            raise exceptions.ParseError("'lat' and 'lon' need to be floating point numbers")
        point = Point(lon, lat, srid=4326)
        queryset = queryset.annotate(distance=Distance('location', point))
        queryset = queryset.annotate(unit_distance=Distance('unit__location', point))
        queryset = queryset.order_by('distance', 'unit_distance')

        if 'distance' in query_params:
            try:
                distance = float(query_params['distance'])
                if not distance > 0:
                    raise ValueError()
            except ValueError:
                raise exceptions.ParseError("'distance' needs to be a floating point number")
            q = Q(location__distance_lte=(point, distance)) | Q(unit__location__distance_lte=(point, distance))
            queryset = queryset.filter(q)
        return queryset


class ResourceListViewSet(munigeo_api.GeoModelAPIView, mixins.ListModelMixin,
                          viewsets.GenericViewSet):
    queryset = Resource.objects.select_related('generic_terms', 'unit', 'type', 'reservation_metadata_set')
    queryset = queryset.prefetch_related('favorited_by', 'resource_equipment', 'purposes', 'images', 'purposes')
    serializer_class = ResourceSerializer
    filter_backends = (filters.SearchFilter, ResourceFilterBackend,
                       LocationFilterBackend, AvailableFilterBackend)
    search_fields = ('name_fi', 'description_fi', 'unit__name_fi',
                     'name_sv', 'description_sv', 'unit__name_sv',
                     'name_en', 'description_en', 'unit__name_en')

    def get_queryset(self):
        if self.request.user.is_staff:
            return self.queryset
        else:
            return self.queryset.filter(public=True)


class ResourceViewSet(munigeo_api.GeoModelAPIView, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = ResourceDetailsSerializer
    queryset = Resource.objects.all()

    def get_queryset(self):
        if self.request.user.is_staff:
            return self.queryset
        else:
            return self.queryset.filter(public=True)

    def _set_favorite(self, request, value):
        resource = self.get_object()
        user = request.user

        exists = user.favorite_resources.filter(id=resource.id).exists()

        if value:
            if not exists:
                user.favorite_resources.add(resource)
                return response.Response(status=status.HTTP_201_CREATED)
            else:
                return response.Response(status=status.HTTP_304_NOT_MODIFIED)
        else:
            if exists:
                user.favorite_resources.remove(resource)
                return response.Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return response.Response(status=status.HTTP_304_NOT_MODIFIED)

    @detail_route(methods=['post'])
    def favorite(self, request, pk=None):
        return self._set_favorite(request, True)

    @detail_route(methods=['post'])
    def unfavorite(self, request, pk=None):
        return self._set_favorite(request, False)

register_view(ResourceListViewSet, 'resource')
register_view(ResourceViewSet, 'resource')
