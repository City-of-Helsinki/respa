from django.utils.translation import ugettext_lazy as _
from rest_framework import mixins, permissions, serializers, viewsets, status, exceptions
from rest_framework.decorators import action
from rest_framework.response import Response

from payments.models import Order, OrderLine, Product
from resources.api.base import register_view
from .integrations import get_payment_provider

from .integrations.bambora_payform import (
    ServiceUnavailableError,
    PayloadValidationError,
    DuplicateOrderError
)


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ('id', 'type', 'name', 'pretax_price', 'price_type', 'tax_percentage')


class OrderLineSerializer(serializers.ModelSerializer):
    price = serializers.SerializerMethodField()

    class Meta:
        model = OrderLine
        fields = ('product', 'quantity', 'price')

    def get_price(self, obj):
        return str(obj.get_price())

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['product'] = ProductSerializer(instance.product).data
        return data


class OrderSerializerBase(serializers.ModelSerializer):
    order_lines = OrderLineSerializer(many=True)
    price = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = '__all__'

    def validate_order_lines(self, value):
        if not value:
            raise serializers.ValidationError(_('At least one order line required.'))
        return value

    def get_price(self, obj):
        if hasattr(obj, '_order_lines'):
            # we are dealing with the price check endpoint and in-memory objects
            order_lines = obj._order_lines
        else:
            order_lines = obj.order_lines.all()
        return str(sum(order_line.get_price() for order_line in order_lines))


class OrderSerializer(OrderSerializerBase):
    return_url = serializers.CharField(write_only=True)
    payment_url = serializers.SerializerMethodField()

    def create(self, validated_data):
        order_lines_data = validated_data.pop('order_lines', [])
        return_url = validated_data.pop('return_url', '')
        order = super().create(validated_data)

        products_bought = []
        for order_line_data in order_lines_data:
            order_line = OrderLine.objects.create(order=order, **order_line_data)
            products_bought.append(order_line.product)

        reservation = order.reservation
        payments = get_payment_provider()
        purchased_items = payments.get_purchased_items(products_bought, reservation)
        customer = payments.get_customer(reservation)

        try:
            self.context['payment_url'] = payments.order_post(
                self.context['request'],
                order.order_number,
                return_url,
                purchased_items,
                customer
            )
        except DuplicateOrderError as doe:
            raise exceptions.APIException(detail=str(doe),
                                          code=status.HTTP_409_CONFLICT)
        except PayloadValidationError as pve:
            raise exceptions.APIException(detail=str(pve),
                                          code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except ServiceUnavailableError as sue:
            raise exceptions.APIException(detail=str(sue),
                                          code=status.HTTP_503_SERVICE_UNAVAILABLE)

        return order

    def get_payment_url(self, obj):
        return self.context.get('payment_url', '')


class PriceEndpointOrderSerializer(OrderSerializerBase):
    class Meta(OrderSerializerBase.Meta):
        fields = ('order_lines', 'reservation', 'price')


class OrderViewSet(mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer

    # TODO We'll probably want something else here when going to production
    permission_classes = (permissions.AllowAny,)

    @action(detail=False, methods=['POST'])
    def check_price(self, request):
        # validate incoming Order and OrderLine data
        write_serializer = PriceEndpointOrderSerializer(data=request.data)
        write_serializer.is_valid(raise_exception=True)

        # build Order and OrderLine objects in memory only
        order_data = write_serializer.validated_data
        order_lines_data = order_data.pop('order_lines')
        order = Order(**order_data)
        order_lines = [OrderLine(order=order, **data) for data in order_lines_data]

        # store the OrderLine objects in the Order object so that we can use
        # those when calculating price for the Order
        order._order_lines = order_lines

        # serialize the in-memory objects
        read_serializer = PriceEndpointOrderSerializer(order)
        order_data = read_serializer.data
        order_data['order_lines'] = [OrderLineSerializer(ol).data for ol in order_lines]

        return Response(order_data, status=200)


class ResourceProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ('id', 'name', 'type', 'pretax_price', 'price_type', 'tax_percentage')


register_view(OrderViewSet, 'order')
