from django.utils.translation import ugettext_lazy as _
from rest_framework import mixins, permissions, serializers, viewsets

from payments.models import Order, OrderLine, Product
from resources.api.base import register_view


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ('id', 'type', 'name', 'pretax_price', 'tax_percentage')


class OrderLineSerializerBase(serializers.ModelSerializer):
    price = serializers.SerializerMethodField()

    class Meta:
        model = OrderLine
        fields = ('product', 'quantity', 'price')

    def get_price(self, obj):
        return str(obj.product.get_price_for_reservation(obj.order.reservation) * obj.quantity)


class OrderLineWriteSerializer(OrderLineSerializerBase):
    pass


class OrderLineReadSerializer(OrderLineSerializerBase):
    product = ProductSerializer()


class OrderWriteSerializer(serializers.ModelSerializer):
    order_lines = OrderLineWriteSerializer(many=True)

    class Meta:
        model = Order
        fields = '__all__'
        read_only_fields = ('status',)

    def create(self, validated_data):
        order_lines_data = validated_data.pop('order_lines', [])
        order = super().create(validated_data)

        for order_line_data in order_lines_data:
            OrderLine.objects.create(order=order, **order_line_data)

        return order

    def validate_order_lines(self, value):
        if not value:
            raise serializers.ValidationError(_('At least one order line required.'))
        return value


class OrderReadSerializer(serializers.ModelSerializer):
    order_lines = OrderLineReadSerializer(many=True)

    class Meta:
        model = Order
        fields = '__all__'


class OrderViewSet(mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = Order.objects.all()

    # TODO We'll probably want something else here when going to production
    permission_classes = (permissions.AllowAny,)

    def get_serializer_class(self):
        if self.action == 'create':
            return OrderWriteSerializer
        else:
            return OrderReadSerializer


class ResourceProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ('id', 'name', 'type', 'pretax_price', 'price_type', 'tax_percentage')


register_view(OrderViewSet, 'order')
