from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from resources.api.base import TranslatedModelSerializer

from ..models import Order, OrderLine, Product


class ProductSerializer(TranslatedModelSerializer):
    id = serializers.CharField(source='product_id')
    tax_percentage = serializers.CharField()

    class Meta:
        model = Product
        fields = (
            'id', 'type', 'name', 'description', 'tax_percentage', 'price', 'price_type', 'price_period', 'max_quantity'
        )


class OrderLineSerializer(serializers.ModelSerializer):
    product = serializers.SlugRelatedField(queryset=Product.objects.current(), slug_field='product_id')
    price = serializers.CharField(source='get_price', read_only=True)
    unit_price = serializers.CharField(source='get_unit_price', read_only=True)

    class Meta:
        model = OrderLine
        fields = ('product', 'quantity', 'unit_price', 'price')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['product'] = ProductSerializer(instance.product).data
        return data

    def validate(self, order_line):
        if order_line.get('quantity', 1) > order_line['product'].max_quantity:
            raise serializers.ValidationError({'quantity': _('Cannot exceed max product quantity')})
        return order_line

    def validate_product(self, product):
        available_products = self.context.get('available_products')
        if available_products is not None:
            if product not in available_products:
                raise serializers.ValidationError(_("This product isn't available on the resource."))
        return product


class OrderSerializerBase(serializers.ModelSerializer):
    order_lines = OrderLineSerializer(many=True)
    price = serializers.CharField(source='get_price', read_only=True)

    class Meta:
        model = Order
        fields = ('state', 'order_lines', 'price')
