import collections
import datetime

import arrow
import django_filters
import pytz
from arrow.parser import ParserError
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils import timezone
from modeltranslation.translator import NotRegistered, translator
from rest_framework import exceptions, filters, mixins, serializers, viewsets

from munigeo import api as munigeo_api

from .models import Purpose, Reservation, Resource, ResourceImage, ResourceType, Unit

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


class PurposeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Purpose.objects.all()
    serializer_class = PurposeSerializer

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
        # FIXME: Get ext from obj.image_format
        kwargs = {'pk': obj.pk, 'ext': 'jpg'}
        url = reverse('resource-image-view', kwargs=kwargs)
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(url)

    class Meta:
        model = ResourceImage
        fields = ('url', 'type', 'caption')
        ordering = ('resource', 'sort_order')


class ResourceSerializer(TranslatedModelSerializer, munigeo_api.GeoModelSerializer):
    purposes = PurposeSerializer(many=True)
    images = NestedResourceImageSerializer(many=True)
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


class ResourceFilterSet(django_filters.FilterSet):
    purpose = django_filters.CharFilter(name="purposes__id", lookup_type='iexact')
    type = django_filters.CharFilter(name="type__id", lookup_type='iexact')

    class Meta:
        model = Resource
        fields = ['purpose', 'type']


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
    search_fields = ('id',)


class ResourceViewSet(munigeo_api.GeoModelAPIView, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Resource.objects.all()
    serializer_class = ResourceDetailsSerializer


register_view(ResourceListViewSet, 'resource')
register_view(ResourceViewSet, 'resource')


class ReservationSerializer(TranslatedModelSerializer, munigeo_api.GeoModelSerializer):
    begin = NullableDateTimeField()
    end = NullableDateTimeField()

    class Meta:
        model = Reservation
        fields = ['url', 'resource', 'user', 'begin', 'end']

    def validate(self, data):
        # if updating a reservation, its identity must be provided to validator
        try:
            reservation = self.context['view'].get_object()
        except AssertionError:
            # the view is a list, which means that we are POSTing a new reservation
            reservation = None
        data['begin'], data['end'] = data['resource'].get_reservation_period(reservation, data=data)
        return data


class ReservationViewSet(munigeo_api.GeoModelAPIView, viewsets.ModelViewSet):
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer

register_view(ReservationViewSet, 'reservation')
