import datetime
import arrow
import pytz
from django.conf import settings
from django.utils.datastructures import MultiValueDictKeyError
from rest_framework import serializers, viewsets, mixins, filters
from modeltranslation.translator import translator, NotRegistered
from munigeo import api as munigeo_api
import django_filters
from django.utils import timezone

from .models import Unit, Resource, Reservation, Purpose


all_views = []
def register_view(klass, name, base_name=None):
    entry = {'class': klass, 'name': name}
    if base_name is not None:
        entry['base_name'] = base_name
    all_views.append(entry)

LANGUAGES = [x[0] for x in settings.LANGUAGES]


class TranslatedModelSerializer(serializers.ModelSerializer):

    def __init__(self, *args, **kwargs):
        super(TranslatedModelSerializer, self).__init__(*args, **kwargs)
        model = self.Meta.model
        try:
            trans_opts = translator.get_options_for_model(model)
        except NotRegistered:
            self.translated_fields = []
            return

        self.translated_fields = trans_opts.fields.keys()
        # Remove the pre-existing data in the bundle.
        for field_name in self.translated_fields:
            for lang in LANGUAGES:
                key = "%s_%s" % (field_name, lang)
                if key in self.fields:
                    del self.fields[key]

    def to_representation(self, obj):
        ret = super(TranslatedModelSerializer, self).to_representation(obj)
        if obj is None:
            return ret

        for field_name in self.translated_fields:
            if field_name not in self.fields:
                continue
            d = {}
            for lang in LANGUAGES:
                key = "%s_%s" % (field_name, lang)
                val = getattr(obj, key, None)
                if val is None:
                    continue
                d[lang] = val

            # If no text provided, leave the field as null
            for key, val in d.items():
                if val is not None:
                    break
            else:
                d = None
            ret[field_name] = d

        return ret

class NullableTimeField(serializers.TimeField):
    def to_representation(self, value):
        if not value:
            return None
        else:
            value = timezone.localtime(value)
        return super().to_representation(value)

class NullableDateTimeField(serializers.DateTimeField):
    def to_representation(self, value):
        if not value:
            return None
        else:
            value = timezone.localtime(value)
        return super().to_representation(value)

class UnitSerializer(TranslatedModelSerializer, munigeo_api.GeoModelSerializer):
    opening_hours_today = serializers.DictField(
        source='get_opening_hours',
        child=serializers.ListField(
            child=serializers.DictField(
                child=NullableDateTimeField())
        )
    )

    class Meta:
        model = Unit


class UnitViewSet(munigeo_api.GeoModelAPIView, viewsets.ReadOnlyModelViewSet):
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer

register_view(UnitViewSet, 'unit')


class PurposeSerializer(TranslatedModelSerializer):
    class Meta:
        model = Purpose
        fields = ['name', 'main_type', 'id']

class ResourceListSerializer(TranslatedModelSerializer, munigeo_api.GeoModelSerializer):
    """
    For listing permanent properties of resources.
    """
    purposes = PurposeSerializer(many=True)

    class Meta:
        model = Resource


class ResourceListFilterSet(django_filters.FilterSet):
    purpose = django_filters.CharFilter(name="purposes__id", lookup_type='iexact')

    class Meta:
        model = Resource
        fields = ['purpose']


class ResourceListViewSet(munigeo_api.GeoModelAPIView, mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = Resource.objects.all()
    serializer_class = ResourceListSerializer
    filter_backends = (filters.SearchFilter, filters.DjangoFilterBackend)
    filter_class = ResourceListFilterSet


register_view(ResourceListViewSet, 'resource')


class ResourceAvailabilitySerializer(TranslatedModelSerializer, munigeo_api.GeoModelSerializer):
    """
    For displaying the status of a single resource during a requested period.
    The resource might be preserialized; in this case just return the
    serialization as is.
    """
    available_hours = serializers.SerializerMethodField()
    opening_hours_today = serializers.DictField(
        source='get_opening_hours',
        child=serializers.ListField(
            child=serializers.DictField(
                child=NullableDateTimeField())
        )
    )
    location = serializers.SerializerMethodField()

    def get_available_hours(self, obj):
        #zone = pytz.timezone(obj.unit.time_zone)
        parameters = self.context['request'].query_params
        start = parameters.get('start', None)
        end = parameters.get('end', None)
        try:
            duration = datetime.timedelta(minutes=int(parameters['duration']))
        except MultiValueDictKeyError:
            duration = None
        hour_list = obj.get_available_hours(start=start, end=end, duration=duration)
        # the hours must be localized when serializing
        #for hours in hour_list:
        #    hours['starts'] = hours['starts'].astimezone(zone)
        #    hours['ends'] = hours['ends'].astimezone(zone)
        return hour_list

    def get_location(self, obj):
        if obj.location:
            return obj.location
        return obj.unit.location

    def to_representation(self, obj):
        if isinstance(obj, dict):
            return obj
        return super().to_representation(obj)


class ResourceSerializer(ResourceListSerializer, ResourceAvailabilitySerializer):
    """
    Mixes resource listing and availability data for displaying a single resource.
    """
    purposes = PurposeSerializer(many=True)

    class Meta:
        model = Resource


class ResourceViewSet(munigeo_api.GeoModelAPIView, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer

register_view(ResourceViewSet, 'resource')


class AvailableSerializer(ResourceAvailabilitySerializer):
    """
    Lists availability data for availability queries.
    """

    class Meta:
        model = Resource
        fields = ['url', 'location', 'available_hours', 'opening_hours']


class AvailableFilterBackEnd(filters.BaseFilterBackend):
    """
    Filters resource availability based on request parameters, requiring
    serializing.
    """

    def filter_queryset(self, request, queryset, view):
        params = request.query_params
        # filtering is only done if at least one parameter is provided
        if 'start' in params or 'end' in params or 'duration' in params:
            serializer = view.serializer_class(context={'request': request})
            serialized_queryset = []
            for resource in queryset:
                serialized_resource = serializer.to_representation(resource)
                if serialized_resource['available_hours'] and serialized_resource['opening_hours']:
                    serialized_queryset.append(serialized_resource)
            return serialized_queryset
        return queryset


class AvailableViewSet(munigeo_api.GeoModelAPIView, mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = Resource.objects.all()
    serializer_class = AvailableSerializer
    filter_backends = (filters.SearchFilter, filters.DjangoFilterBackend, AvailableFilterBackEnd)
    filter_class = ResourceListFilterSet

register_view(AvailableViewSet, 'available')


class ReservationSerializer(TranslatedModelSerializer, munigeo_api.GeoModelSerializer):
    begin = NullableDateTimeField()
    end = NullableDateTimeField()

    class Meta:
        model = Reservation
        fields = ['resource', 'user', 'begin', 'end']


class ReservationViewSet(munigeo_api.GeoModelAPIView, viewsets.ModelViewSet):
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer

register_view(ReservationViewSet, 'reservation')
