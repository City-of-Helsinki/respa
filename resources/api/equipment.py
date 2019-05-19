from rest_framework import viewsets
import django_filters
from .base import TranslatedModelSerializer, register_view
from resources.models import Equipment, EquipmentAlias, EquipmentCategory


class PlainEquipmentSerializer(TranslatedModelSerializer):
    class Meta:
        model = Equipment
        fields = ('name', 'id')


class EquipmentCategorySerializer(TranslatedModelSerializer):
    equipment = PlainEquipmentSerializer(many=True)

    class Meta:
        model = EquipmentCategory
        fields = ('name', 'id', 'equipment')


class PlainEquipmentCategorySerializer(TranslatedModelSerializer):
    class Meta:
        model = EquipmentCategory
        fields = ('name', 'id')


class EquipmentCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = EquipmentCategory.objects.all()
    serializer_class = EquipmentCategorySerializer


register_view(EquipmentCategoryViewSet, 'equipment_category')


class EquipmentAliasSerializer(TranslatedModelSerializer):
    class Meta:
        model = EquipmentAlias
        fields = ('name', 'language')


class EquipmentSerializer(TranslatedModelSerializer):
    aliases = EquipmentAliasSerializer(many=True)
    category = PlainEquipmentCategorySerializer()

    class Meta:
        model = Equipment
        fields = ('name', 'id', 'aliases', 'category')


class EquipmentFilterSet(django_filters.FilterSet):
    resource_group = django_filters.Filter(field_name='resource_equipment__resource__groups__identifier', lookup_expr='in',
                                           widget=django_filters.widgets.CSVWidget, distinct=True)

    class Meta:
        model = Equipment
        fields = ('resource_group',)


class EquipmentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Equipment.objects.all()
    serializer_class = EquipmentSerializer
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,)
    filterset_class = EquipmentFilterSet


register_view(EquipmentViewSet, 'equipment')
