from rest_framework import serializers

from resources.api.resource import ResourceDetailsSerializer, ResourceSerializer

from .base import ProductSerializer
from ..models import ARCHIVED_AT_NONE


class PaymentsResourceSerializerMixin(serializers.ModelSerializer):
    products = serializers.SerializerMethodField()

    def get_products(self, obj):
        product_list = obj.products.all()

        # Use python filter function to filter the queryset to prevent query to DB if products have been refetched
        filtered_product_list = list(filter(lambda product: product.archived_at == ARCHIVED_AT_NONE, list(product_list)))
        return ProductSerializer(filtered_product_list, many=True).data


class PaymentsResourceSerializer(PaymentsResourceSerializerMixin, ResourceSerializer):
    pass


class PaymentsResourceDetailsSerializer(PaymentsResourceSerializerMixin, ResourceDetailsSerializer):
    pass
