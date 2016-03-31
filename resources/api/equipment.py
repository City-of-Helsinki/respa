from rest_framework import viewsets

from .base import TranslatedModelSerializer, register_view
from resources.models import Equipment, EquipmentAlias, EquipmentCategory


class PlainEquipmentSerializer(TranslatedModelSerializer):
    class Meta:
        model = Equipment
        fields = ('name', 'id')


class EquipmentCategorySerializer(TranslatedModelSerializer):

    class Meta:
        model = EquipmentCategory
        fields = ('name', 'id', 'equipment')
    equipment = PlainEquipmentSerializer(many=True)


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

    class Meta:
        model = Equipment
        fields = ('name', 'id', 'aliases', 'category')
    aliases = EquipmentAliasSerializer(many=True)
    category = PlainEquipmentCategorySerializer()


class EquipmentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Equipment.objects.all()
    serializer_class = EquipmentSerializer

register_view(EquipmentViewSet, 'equipment')
