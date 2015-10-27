from rest_framework import serializers, viewsets

from munigeo import api as munigeo_api
from resources.api.base import NullableDateTimeField, TranslatedModelSerializer, register_view
from resources.models import Unit


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
