from django.conf import settings
from rest_framework import serializers, viewsets, generics
from modeltranslation.translator import translator, NotRegistered
from munigeo import api as munigeo_api

from .models import Unit, Resource, Reservation


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


class UnitSerializer(TranslatedModelSerializer, munigeo_api.GeoModelSerializer):
    opening_hours_today = serializers.DictField(child=NullableTimeField(),
                                                source='get_opening_hours')

    class Meta:
        model = Unit


class UnitViewSet(munigeo_api.GeoModelAPIView, viewsets.ReadOnlyModelViewSet):
    queryset = Unit.objects.all()
    serializer_class = UnitSerializer

register_view(UnitViewSet, 'unit')


class ResourceSerializer(TranslatedModelSerializer, munigeo_api.GeoModelSerializer):
    opening_hours_today = serializers.DictField(child=NullableTimeField(),
                                                source='get_opening_hours')

    class Meta:
        model = Resource


class ResourceViewSet(munigeo_api.GeoModelAPIView, viewsets.ReadOnlyModelViewSet):
    queryset = Resource.objects.all()
    serializer_class = ResourceSerializer

register_view(ResourceViewSet, 'resource')


class ReservationSerializer(TranslatedModelSerializer, munigeo_api.GeoModelSerializer):

    class Meta:
        model = Reservation


class ReservationViewSet(munigeo_api.GeoModelAPIView, viewsets.ModelViewSet):
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer

register_view(ReservationViewSet, 'reservation')
