from django.utils.translation import ugettext_lazy as _
from rest_framework import mixins, permissions, serializers, viewsets

from payments.models import Order, OrderLine, Product
from resources.api.base import register_view
from .integrations.bambora_payform import BamboraPayformPayments


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
    redirect_url = serializers.CharField(write_only=True)

    class Meta:
        model = Order
        fields = '__all__'
        read_only_fields = ('status',)

    def create(self, validated_data):
        order_lines_data = validated_data.pop('order_lines', [])
        redirect_url = validated_data.pop('redirect_url', '')
        order = super().create(validated_data)

        products_bought = []
        for order_line_data in order_lines_data:
            order_line = OrderLine.objects.create(order=order, **order_line_data)
            products_bought.append(order_line.product)

        reservation = order.reservation
        payments = BamboraPayformPayments()
        purchased_items = payments.get_purchased_items(products_bought, reservation)
        customer = payments.get_customer(reservation)
        payment_url = payments.order_post(order.order_number, redirect_url, purchased_items, customer)

        # TODO Redirect to payment, order.status = Order.WAITING, save order & orderlines after
        print(payment_url)

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
