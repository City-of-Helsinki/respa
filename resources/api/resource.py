import collections
import datetime

import arrow
import django_filters
import pytz
from arrow.parser import ParserError

from django import forms
from django.db.models import Prefetch, Q
from django.urls import reverse
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from resources.pagination import PurposePagination
from rest_framework import exceptions, filters, mixins, serializers, viewsets, response, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from guardian.core import ObjectPermissionChecker

from munigeo import api as munigeo_api
from resources.models import (
    Purpose, Reservation, Resource, ResourceImage, ResourceType, ResourceEquipment,
    TermsOfUse, Equipment, ReservationMetadataSet, ResourceDailyOpeningHours
)
from resources.models.resource import determine_hours_time_range

from ..auth import is_general_admin, is_staff
from .base import TranslatedModelSerializer, register_view, DRFFilterBooleanWidget
from .reservation import ReservationSerializer
from .unit import UnitSerializer
from .equipment import EquipmentSerializer
from rest_framework.settings import api_settings as drf_settings


def parse_query_time_range(params):
    times = {}
    for name in ('start', 'end'):
        if name not in params:
            continue
        try:
            times[name] = arrow.get(params[name]).to('utc').datetime
        except ParserError:
            raise exceptions.ParseError("'%s' must be a timestamp in ISO 8601 format" % name)

    if len(times):
        if 'start' not in times or 'end' not in times:
            raise exceptions.ParseError("You must supply both 'start' and 'end'")
        if times['end'] < times['start']:
            raise exceptions.ParseError("'end' must be after 'start'")

    return times


def get_resource_reservations_queryset(begin, end):
    qs = Reservation.objects.filter(begin__lte=end, end__gte=begin).current()
    qs = qs.order_by('begin').prefetch_related('catering_orders').select_related('user')
    return qs


class PurposeSerializer(TranslatedModelSerializer):
    class Meta:
        model = Purpose
        fields = ['name', 'parent', 'id']


class PurposeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Purpose.objects.all()
    serializer_class = PurposeSerializer
    pagination_class = PurposePagination

    def get_queryset(self):
        if is_staff(self.request.user):
            return self.queryset
        else:
            return self.queryset.filter(public=True)


register_view(PurposeViewSet, 'purpose')


class ResourceTypeSerializer(TranslatedModelSerializer):
    class Meta:
        model = ResourceType
        fields = ['name', 'main_type', 'id']


class ResourceTypeFilterSet(django_filters.FilterSet):
    resource_group = django_filters.Filter(field_name='resource__groups__identifier', lookup_expr='in',
                                           widget=django_filters.widgets.CSVWidget, distinct=True)

    class Meta:
        model = ResourceType
        fields = ('resource_group',)


class ResourceTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ResourceType.objects.all()
    serializer_class = ResourceTypeSerializer
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,)
    filterset_class = ResourceTypeFilterSet


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
    equipment = EquipmentSerializer()

    class Meta:
        model = ResourceEquipment
        fields = ('equipment', 'data', 'id', 'description')

    def to_representation(self, obj):
        # remove unnecessary nesting and aliases
        if 'equipment_cache' in self.context:
            obj.equipment = self.context['equipment_cache'][obj.equipment_id]
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
    # FIXME: Enable available_hours when it's more performant
    # available_hours = serializers.SerializerMethodField()
    opening_hours = serializers.SerializerMethodField()
    reservations = serializers.SerializerMethodField()
    user_permissions = serializers.SerializerMethodField()
    supported_reservation_extra_fields = serializers.ReadOnlyField(source='get_supported_reservation_extra_field_names')
    required_reservation_extra_fields = serializers.ReadOnlyField(source='get_required_reservation_extra_field_names')
    is_favorite = serializers.SerializerMethodField()
    generic_terms = serializers.SerializerMethodField()
    # deprecated, backwards compatibility
    reservable_days_in_advance = serializers.ReadOnlyField(source='get_reservable_max_days_in_advance')
    reservable_max_days_in_advance = serializers.ReadOnlyField(source='get_reservable_max_days_in_advance')
    reservable_before = serializers.SerializerMethodField()
    reservable_min_days_in_advance = serializers.ReadOnlyField(source='get_reservable_min_days_in_advance')
    reservable_after = serializers.SerializerMethodField()

    def get_user_permissions(self, obj):
        request = self.context.get('request', None)
        return {
            'can_make_reservations': obj.can_make_reservations(request.user) if request else False,
            'can_ignore_opening_hours': obj.can_ignore_opening_hours(request.user) if request else False,
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

    def get_reservable_after(self, obj):
        request = self.context.get('request')
        user = request.user if request else None

        if user and obj.is_admin(user):
            return None
        else:
            return obj.get_reservable_after()

    def to_representation(self, obj):
        # we must parse the time parameters before serializing
        self.parse_parameters()
        if isinstance(obj, dict):
            # resource is already serialized
            return obj

        # We cache the metadata objects to save on SQL roundtrips
        if 'reservation_metadata_set_cache' in self.context:
            set_id = obj.reservation_metadata_set_id
            if set_id:
                obj.reservation_metadata_set = self.context['reservation_metadata_set_cache'][set_id]
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
        times = parse_query_time_range(params)

        if 'duration' in params:
            try:
                times['duration'] = int(params['duration'])
            except ValueError:
                raise exceptions.ParseError("'duration' must be supplied as an integer")

        if 'during_closing' in params:
            during_closing = params['during_closing'].lower()
            if during_closing == 'true' or during_closing == 'yes' or during_closing == '1':
                times['during_closing'] = True

        if len(times):
            self.context.update(times)

    def get_opening_hours(self, obj):
        if 'start' in self.context:
            start = self.context['start']
            end = self.context['end']
        else:
            start = None
            end = None

        hours_cache = self.context.get('opening_hours_cache', {}).get(obj.id)
        hours_by_date = obj.get_opening_hours(start, end, opening_hours_cache=hours_cache)

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

        if 'reservations_cache' in self.context:
            rv_list = self.context['reservations_cache'].get(obj.id, [])
            for rv in rv_list:
                rv.resource = obj
        else:
            rv_list = get_resource_reservations_queryset(self.context['start'], self.context['end'])
            rv_list = rv_list.filter(resource=obj)

        rv_ser_list = ReservationSerializer(rv_list, many=True, context=self.context).data
        return rv_ser_list

    class Meta:
        model = Resource
        exclude = ('reservation_requested_notification_extra', 'reservation_confirmed_notification_extra',
                   'access_code_type', 'reservation_metadata_set')


class ResourceDetailsSerializer(ResourceSerializer):
    unit = UnitSerializer()


class ParentFilter(django_filters.Filter):
    """
    Filter that also checks the parent field
    """

    def filter(self, qs, value):
        child_matches = super().filter(qs, value)
        self.field_name = self.field_name.replace('__id', '__parent__id')
        parent_matches = super().filter(qs, value)
        return child_matches | parent_matches


class ParentCharFilter(ParentFilter):
    field_class = forms.CharField


class ResourceFilterSet(django_filters.FilterSet):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)

    purpose = ParentCharFilter(field_name='purposes__id', lookup_expr='iexact')
    type = django_filters.Filter(field_name='type__id', lookup_expr='in', widget=django_filters.widgets.CSVWidget)
    people = django_filters.NumberFilter(field_name='people_capacity', lookup_expr='gte')
    need_manual_confirmation = django_filters.BooleanFilter(field_name='need_manual_confirmation',
                                                            widget=DRFFilterBooleanWidget)
    is_favorite = django_filters.BooleanFilter(method='filter_is_favorite', widget=DRFFilterBooleanWidget)
    unit = django_filters.CharFilter(field_name='unit__id', lookup_expr='iexact')
    resource_group = django_filters.Filter(field_name='groups__identifier', lookup_expr='in',
                                           widget=django_filters.widgets.CSVWidget, distinct=True)
    equipment = django_filters.Filter(field_name='resource_equipment__equipment__id', lookup_expr='in',
                                      widget=django_filters.widgets.CSVWidget, distinct=True)
    available_between = django_filters.Filter(method='filter_available_between',
                                              widget=django_filters.widgets.CSVWidget)
    free_of_charge = django_filters.BooleanFilter(method='filter_free_of_charge',
                                                  widget=DRFFilterBooleanWidget)
    municipality = django_filters.Filter(field_name='unit__municipality_id', lookup_expr='in',
                                         widget=django_filters.widgets.CSVWidget, distinct=True)
    order_by = django_filters.OrderingFilter(
        fields=(
            ('name_fi', 'resource_name_fi'),
            ('name_en', 'resource_name_en'),
            ('name_sv', 'resource_name_sv'),
            ('unit__name_fi', 'unit_name_fi'),
            ('unit__name_en', 'unit_name_en'),
            ('unit__name_sv', 'unit_name_sv'),
            ('type__name_fi', 'type_name_fi'),
            ('type__name_en', 'type_name_en'),
            ('type__name_sv', 'type_name_sv'),
            ('people_capacity', 'people_capacity'),
        ),
    )

    def filter_is_favorite(self, queryset, name, value):
        if not self.user.is_authenticated:
            if value:
                return queryset.none()
            else:
                return queryset

        if value:
            return queryset.filter(favorited_by=self.user)
        else:
            return queryset.exclude(favorited_by=self.user)

    def filter_free_of_charge(self, queryset, name, value):
        qs = Q(min_price_per_hour__lte=0) | Q(min_price_per_hour__isnull=True)
        if value:
            return queryset.filter(qs)
        else:
            return queryset.exclude(qs)

    def _deserialize_datetime(self, value):
        try:
            return arrow.get(value).datetime
        except ParserError:
            raise exceptions.ParseError("'%s' must be a timestamp in ISO 8601 format" % value)

    def filter_available_between(self, queryset, name, value):
        if len(value) < 2 or len(value) > 3:
            raise exceptions.ParseError('available_between takes two or three comma-separated values.')

        available_start = self._deserialize_datetime(value[0])
        available_end = self._deserialize_datetime(value[1])

        if available_start.date() != available_end.date():
            raise exceptions.ParseError('available_between timestamps must be on the same day.')
        overlapping_reservations = Reservation.objects.filter(
            resource__in=queryset, end__gt=available_start, begin__lt=available_end
        ).current()

        if len(value) == 2:
            return self._filter_available_between_whole_range(
                queryset, overlapping_reservations, available_start, available_end
            )
        else:
            try:
                period = datetime.timedelta(minutes=int(value[2]))
            except ValueError:
                raise exceptions.ParseError('available_between period must be an integer.')
            return self._filter_available_between_with_period(
                queryset, overlapping_reservations, available_start, available_end, period
            )

    def _filter_available_between_whole_range(self, queryset, reservations, available_start, available_end):
        # exclude resources that have reservation(s) overlapping with the available_between range
        queryset = queryset.exclude(reservations__in=reservations)
        closed_resource_ids = {
            resource.id
            for resource in queryset
            if not self._is_resource_open(resource, available_start, available_end)
        }

        return queryset.exclude(id__in=closed_resource_ids)

    @staticmethod
    def _is_resource_open(resource, start, end):
        opening_hours = resource.get_opening_hours(start, end)
        if len(opening_hours) > 1:
            # range spans over multiple days, assume resources aren't open all night and skip the resource
            return False

        hours = next(iter(opening_hours.values()))[0]  # assume there is only one hours obj per day
        if not hours['opens'] and not hours['closes']:
            return False

        start_too_early = hours['opens'] and start < hours['opens']
        end_too_late = hours['closes'] and end > hours['closes']
        if start_too_early or end_too_late:
            return False

        return True

    def _filter_available_between_with_period(self, queryset, reservations, available_start, available_end, period):
        reservations = reservations.order_by('begin').select_related('resource')

        reservations_by_resource = collections.defaultdict(list)
        for reservation in reservations:
            reservations_by_resource[reservation.resource_id].append(reservation)

        available_resources = set()

        hours_qs = ResourceDailyOpeningHours.objects.filter(
            open_between__overlap=(available_start, available_end, '[)'))

        # check the resources one by one to determine which ones have open slots
        for resource in queryset.prefetch_related(None).prefetch_related(
                Prefetch('opening_hours', queryset=hours_qs, to_attr='prefetched_opening_hours')):
            reservations = reservations_by_resource[resource.id]

            if self._is_resource_available(resource, available_start, available_end, reservations, period):
                available_resources.add(resource.id)

        return queryset.filter(id__in=available_resources)

    @staticmethod
    def _is_resource_available(resource, available_start, available_end, reservations, period):
        opening_hours = resource.get_opening_hours(available_start, available_end, resource.prefetched_opening_hours)
        hours = next(iter(opening_hours.values()))[0]  # assume there is only one hours obj per day

        if not (hours['opens'] or hours['closes']):
            return False

        current = max(available_start, hours['opens']) if hours['opens'] is not None else available_start
        end = min(available_end, hours['closes']) if hours['closes'] is not None else available_end

        if current >= end:
            # the resource is already closed
            return False

        if not reservations:
            # the resource has no reservations, just check if the period fits in the resource's opening times
            if end - current >= period:
                return True
            return False

        # try to find an open slot between reservations and opening / closing times.
        # start from period start time or opening time depending on which one is earlier.
        for reservation in reservations:
            if reservation.end <= current:
                # this reservation is in the past
                continue
            if reservation.begin - current >= period:
                # found an open slot before the reservation currently being examined
                return True
            if reservation.end > end:
                # the reservation currently being examined ends after the period or closing time,
                # so no free slots
                return False
            # did not find an open slot before the reservation currently being examined,
            # proceed to next reservation
            current = reservation.end
        else:
            # all reservations checked and no free slot found, check if there is a free slot after the last
            # reservation
            if end - reservation.end >= period:
                return True

        return False

    class Meta:
        model = Resource
        fields = ['purpose', 'type', 'people', 'need_manual_confirmation', 'is_favorite', 'unit', 'available_between', 'min_price_per_hour']


class ResourceFilterBackend(filters.BaseFilterBackend):
    """
    Make request user available in the filter set.
    """

    def filter_queryset(self, request, queryset, view):
        return ResourceFilterSet(request.query_params, queryset=queryset, user=request.user).qs


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


class ResourceCacheMixin:
    def _preload_opening_hours(self, times):
        # We have to evaluate the query here to make sure all the
        # resources are on the same timezone. In case of different
        # time zones, we skip this optimization.
        time_zone = None
        hours_by_resource = {}
        for resource in self._page:
            if time_zone:
                if resource.unit.time_zone != time_zone:
                    return None
            else:
                time_zone = resource.unit.time_zone
            hours_by_resource[resource.id] = []
        if not time_zone:
            return None

        begin, end = determine_hours_time_range(times.get('start'), times.get('end'), pytz.timezone(time_zone))
        hours = ResourceDailyOpeningHours.objects.filter(
            resource__in=self._page, open_between__overlap=(begin, end, '[)')
        )
        for obj in hours:
            hours_by_resource[obj.resource_id].append(obj)
        return hours_by_resource

    def _preload_reservations(self, times):
        qs = get_resource_reservations_queryset(times['start'], times['end'])
        reservations = qs.filter(resource__in=self._page)
        reservations_by_resource = {}
        for rv in reservations:
            rv_list = reservations_by_resource.setdefault(rv.resource_id, [])
            rv_list.append(rv)
        return reservations_by_resource

    def _preload_permissions(self):
        units = set()
        resource_groups = set()
        checker = ObjectPermissionChecker(self.request.user)
        for res in self._page:
            units.add(res.unit)
            for g in res.groups.all():
                resource_groups.add(g)
            res._permission_checker = checker

        if units:
            checker.prefetch_perms(units)
        if resource_groups:
            checker.prefetch_perms(resource_groups)

    def _get_cache_context(self):
        context = {}

        equipment_list = Equipment.objects.filter(resource_equipment__resource__in=self._page).distinct().\
            select_related('category').prefetch_related('aliases')
        equipment_cache = {x.id: x for x in equipment_list}

        context['equipment_cache'] = equipment_cache
        set_list = ReservationMetadataSet.objects.all().prefetch_related('supported_fields', 'required_fields')
        context['reservation_metadata_set_cache'] = {x.id: x for x in set_list}

        times = parse_query_time_range(self.request.query_params)
        if times:
            context['reservations_cache'] = self._preload_reservations(times)
        context['opening_hours_cache'] = self._preload_opening_hours(times)

        self._preload_permissions()

        return context


class ResourceListViewSet(munigeo_api.GeoModelAPIView, mixins.ListModelMixin,
                          viewsets.GenericViewSet, ResourceCacheMixin):
    queryset = Resource.objects.select_related('generic_terms', 'unit', 'type', 'reservation_metadata_set')
    queryset = queryset.prefetch_related('favorited_by', 'resource_equipment', 'resource_equipment__equipment',
                                         'purposes', 'images', 'purposes', 'groups')
    filter_backends = (filters.SearchFilter, ResourceFilterBackend, LocationFilterBackend)
    search_fields = ('name_fi', 'description_fi', 'unit__name_fi',
                     'name_sv', 'description_sv', 'unit__name_sv',
                     'name_en', 'description_en', 'unit__name_en')
    authentication_classes = (
        list(drf_settings.DEFAULT_AUTHENTICATION_CLASSES) +
        [SessionAuthentication])

    def get_serializer_class(self):
        query_params = self.request.query_params
        if query_params.get('include') == 'unit_detail':
            return ResourceDetailsSerializer
        return ResourceSerializer

    def get_serializer(self, page, *args, **kwargs):
        self._page = page
        return super().get_serializer(page, *args, **kwargs)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update(self._get_cache_context())
        return context

    def get_queryset(self):
        return self.queryset.visible_for(self.request.user)


class ResourceViewSet(munigeo_api.GeoModelAPIView, mixins.RetrieveModelMixin,
                      viewsets.GenericViewSet, ResourceCacheMixin):
    serializer_class = ResourceDetailsSerializer
    queryset = ResourceListViewSet.queryset

    def get_serializer(self, page, *args, **kwargs):
        self._page = [page]
        return super().get_serializer(page, *args, **kwargs)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update(self._get_cache_context())
        return context

    def get_queryset(self):
        return self.queryset.visible_for(self.request.user)

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

    @action(detail=True, methods=['post'])
    def favorite(self, request, pk=None):
        return self._set_favorite(request, True)

    @action(detail=True, methods=['post'])
    def unfavorite(self, request, pk=None):
        return self._set_favorite(request, False)


register_view(ResourceListViewSet, 'resource')
register_view(ResourceViewSet, 'resource')
