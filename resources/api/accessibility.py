from rest_framework import serializers
from .base import TranslatedModelSerializer
from resources.models import AccessibilityViewpoint, ResourceAccessibility, UnitAccessibility


class AccessibilityViewpointSerializer(TranslatedModelSerializer):
    class Meta:
        model = AccessibilityViewpoint
        fields = ('id', 'name')


class ResourceAccessibilitySerializer(TranslatedModelSerializer):
    value = serializers.SerializerMethodField()
    viewpoint_id = serializers.SerializerMethodField()
    viewpoint_name = serializers.SerializerMethodField()

    class Meta:
        model = ResourceAccessibility
        fields = ('viewpoint_id', 'viewpoint_name', 'value', 'shortage_count')

    def get_value(self, obj):
        return obj.value.value

    def get_viewpoint_id(self, obj):
        return obj.viewpoint_id

    def get_viewpoint_name(self, obj):
        return AccessibilityViewpointSerializer(obj.viewpoint).data['name']


class UnitAccessibilitySerializer(TranslatedModelSerializer):
    value = serializers.SerializerMethodField()
    viewpoint_id = serializers.SerializerMethodField()
    viewpoint_name = serializers.SerializerMethodField()

    class Meta:
        model = UnitAccessibility
        fields = ('viewpoint_id', 'viewpoint_name', 'value', 'shortage_count')

    def get_value(self, obj):
        return obj.value.value

    def get_viewpoint_id(self, obj):
        return obj.viewpoint_id

    def get_viewpoint_name(self, obj):
        return AccessibilityViewpointSerializer(obj.viewpoint).data['name']


