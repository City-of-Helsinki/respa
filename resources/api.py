import datetime
import arrow
import pytz
from django.conf import settings
from django.utils.datastructures import MultiValueDictKeyError
from rest_framework import serializers, viewsets, generics, filters
from modeltranslation.translator import translator, NotRegistered
from munigeo import api as munigeo_api
import django_filters

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
        return super().to_representation(value)

class NullableDateTimeField(serializers.DateTimeField):
    def to_representation(self, value):
        if not value:
            return None
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


class ResourceSerializer(TranslatedModelSerializer, munigeo_api.GeoModelSerializer):
    available_hours = serializers.SerializerMethodField()
    opening_hours_today = serializers.DictField(
        source='get_opening_hours',
        child=serializers.ListField(
            child=serializers.DictField(
                child=NullableDateTimeField())
        )
    )

    purposes = PurposeSerializer(many=True)

    class Meta:
        model = Resource

    def get_available_hours(self, obj):
        zone = pytz.timezone(obj.unit.time_zone)
        parameters = self.context['request'].query_params
        try:
            duration = datetime.timedelta(minutes=int(parameters['duration']))
        except MultiValueDictKeyError:
            duration = None
        try:
            start = zone.localize(arrow.get(parameters['start']).naive)
        except MultiValueDictKeyError:
            start = None
        try:
            end = zone.localize(arrow.get(parameters['end']).naive)
        except MultiValueDictKeyError:
            end = None
        hour_list = obj.get_available_hours(start=start, end=end, duration=duration)
        # the hours must be localized when serializing
        for hours in hour_list:
            hours['starts'] = hours['starts'].astimezone(zone)
            hours['ends'] = hours['ends'].astimezone(zone)
        return hour_list


def filter_by_availability(queryset, value):
    # TODO: implement by preserializing, adding available_hours dict to queryset
    return queryset


class ResourceFilter(django_filters.FilterSet):
    purpose = django_filters.CharFilter(name="purposes__id", lookup_type='iexact')
    start = django_filters.CharFilter(action=filter_by_availability)
    end = django_filters.CharFilter(action=filter_by_availability)
    duration = django_filters.CharFilter(action=filter_by_availability)

    class Meta:
        model = Resource
        fields = ['purpose']


class ResourceViewSet(munigeo_api.GeoModelAPIView, viewsets.ReadOnlyModelViewSet):
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer
    filter_backends = (filters.SearchFilter, filters.DjangoFilterBackend)
    filter_class = ResourceFilter

register_view(ResourceViewSet, 'resource')


class ReservationSerializer(TranslatedModelSerializer, munigeo_api.GeoModelSerializer):

    class Meta:
        model = Reservation
        fields = ['resource', 'begin', 'end', 'user']


class ReservationViewSet(munigeo_api.GeoModelAPIView, viewsets.ModelViewSet):
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer

register_view(ReservationViewSet, 'reservation')
