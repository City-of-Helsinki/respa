from rest_framework import serializers

from resources.api.resource import ResourceDetailsSerializer, ResourceSerializer

from .base import ProductSerializer


class PaymentsResourceSerializerMixin(serializers.ModelSerializer):
    products = serializers.SerializerMethodField()

    def get_products(self, obj):
        return ProductSerializer(obj.products.current(), many=True).data


class PaymentsResourceSerializer(PaymentsResourceSerializerMixin, ResourceSerializer):
    pass


class PaymentsResourceDetailsSerializer(PaymentsResourceSerializerMixin, ResourceDetailsSerializer):
    pass
