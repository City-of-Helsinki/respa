import collections
import datetime

import arrow
import django_filters
import pytz
from arrow.parser import ParserError
from django import forms
from django.core.urlresolvers import reverse
from rest_framework import exceptions, filters, mixins, serializers, viewsets

from munigeo import api as munigeo_api
from resources.models import Purpose, Resource, ResourceImage, ResourceType, ResourceEquipment
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
    paginate_by = 50

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

    def to_representation(self, obj):
        # we must parse the time parameters before serializing
        self.parse_parameters()
        if isinstance(obj, dict):
            # resource is already serialized
            return obj
        ret = super().to_representation(obj)
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
        for res in res_ser_list:
            del res['resource']
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

        hour_list = obj.get_available_hours(start=self.context['start'],
                                            end=self.context['end'],
                                            duration=duration)
        # the hours must be localized when serializing
        for hours in hour_list:
            hours['starts'] = hours['starts'].astimezone(zone)
            hours['ends'] = hours['ends'].astimezone(zone)
        return hour_list

    class Meta:
        model = Resource


class ResourceDetailsSerializer(ResourceSerializer):
    unit = UnitSerializer()


class ParentFilter(django_filters.Filter):
    """
    Filter that also checks the parent field
    """

    def filter(self, qs, value):
        child_matches = super().filter(qs, value)
        self.name=self.name.replace('__id', '__parent__id')
        parent_matches = super().filter(qs, value)
        return child_matches | parent_matches


class ParentCharFilter(ParentFilter):
    field_class = forms.CharField


class ResourceFilterSet(django_filters.FilterSet):
    purpose = ParentCharFilter(name="purposes__id", lookup_type='iexact')
    type = django_filters.CharFilter(name="type__id", lookup_type='iexact')
    people = django_filters.NumberFilter(name="people_capacity", lookup_type='gte')

    class Meta:
        model = Resource
        fields = ['purpose', 'type', 'people']


class AvailableFilterBackEnd(filters.BaseFilterBackend):
    """
    Filters resource availability based on request parameters, requiring
    serializing.
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


class ResourceListViewSet(munigeo_api.GeoModelAPIView, mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer
    filter_backends = (filters.SearchFilter, filters.DjangoFilterBackend, AvailableFilterBackEnd)
    filter_class = ResourceFilterSet
    search_fields = ('name', 'description', 'unit__name')


class ResourceViewSet(munigeo_api.GeoModelAPIView, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Resource.objects.all()
    serializer_class = ResourceDetailsSerializer


register_view(ResourceListViewSet, 'resource')
register_view(ResourceViewSet, 'resource')
