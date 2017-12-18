from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import PermissionDenied
from rest_framework import viewsets, serializers
from rest_framework.exceptions import ValidationError
from munigeo import api as munigeo_api
from resources.models import Resource, Unit, ResourceType
from resources.api.resource import ResourceSerializer
from resources.api.base import TranslatedModelSerializer


class SimpleUnitSerializer(TranslatedModelSerializer):
    name = serializers.CharField(required=True)

    class Meta:
        model = Unit
        fields = '__all__'


class ResourceSerializer(ResourceSerializer):
    name = serializers.CharField(required=True)
    name_fi = serializers.CharField(required=True)
    description = serializers.CharField(required=False)
    description_fi = serializers.CharField(required=False)
    type_id = serializers.CharField(max_length=100)
    unit_id = serializers.CharField(max_length=50)
    unit = SimpleUnitSerializer(read_only=True)

    def parse_parameters(self):
        pass

    def validate(self, data):
        request_user = self.context['request'].user
        return data

    def validate_name(self, value):
        if not value:
            raise ValidationError('Berth name is required')

    def validate_name_fi(self, value):
        if not value:
            raise ValidationError('Berth name is required')

    def to_internal_value(self, data):
        type_instance = None
        unit_instance = None
        type_id = data.get('type_id', None)

        if type_id != None:
            if not ResourceType.objects.filter(pk=type_id).exists():
                raise ValidationError(dict(access_code=_('Invalid type id')))
            type_instance = ResourceType.objects.get(pk=type_id)
        else:
            types = ResourceType.objects.all();
            for type in types:
                if 'vene' in type.name or 'Vene' in type.name or 'boat' in type.name or 'Boat' in type.name:
                    type_instance = type

        if type_instance == None:
            raise ValidationError(dict(access_code=_('Invalid type id')))

        if not Unit.objects.filter(pk=data.get('unit_id')).exists():
            raise ValidationError(dict(access_code=_('Invalid unit id')))

        unit_instance = Unit.objects.get(pk=data.get('unit_id'))

        return {
            'authentication': 'none',
            'name': data.get('name'),
            'name_fi': data.get('name_fi'),
            'description': data.get('description'),
            'description_fi': data.get('description_fi'),
            'unit': unit_instance,
            'type': type_instance,
            'reservable': data.get('reservable')
        }
