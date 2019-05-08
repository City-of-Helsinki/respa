from django.utils.translation import ugettext_lazy as _
from rest_framework import mixins, permissions, serializers, viewsets, status, exceptions
from rest_framework.decorators import action
from rest_framework.response import Response

from payments.models import Order, OrderLine, Product
from resources.api.base import register_view, TranslatedModelSerializer
from .integrations import get_payment_provider

from .integrations.bambora_payform import (
    ServiceUnavailableError,
    PayloadValidationError,
    DuplicateOrderError
)


class ProductSerializer(TranslatedModelSerializer):
    id = serializers.IntegerField(source='product_id')

    class Meta:
        model = Product
        fields = ('id', 'type', 'name', 'pretax_price', 'price_type', 'tax_percentage')


class OrderLineSerializerBase(serializers.ModelSerializer):
    price = serializers.SerializerMethodField()
    product = serializers.SlugRelatedField(queryset=Product.objects.current(), slug_field='product_id')

    class Meta:
        model = OrderLine
        fields = ('product', 'quantity', 'price')

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['product'] = ProductSerializer(instance.product).data
        return data


class OrderLineSerializer(OrderLineSerializerBase):
    def get_price(self, obj):
        return str(obj.get_price())


class PriceEndpointOrderLineSerializer(OrderLineSerializerBase):
    def get_price(self, obj):
        return str(calculate_in_memory_order_line_price(obj, obj.order._begin, obj.order._end))


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

    def get_price(self, obj):
        return str(obj.get_price())


class PriceEndpointOrderSerializer(OrderSerializerBase):
    order_lines = PriceEndpointOrderLineSerializer(many=True)

    # these fields are actually returned from the API as well, but because
    # they are non-model fields, it seems to be easier to mark them as write
    # only and add them manually to returned data in the viewset
    begin = serializers.DateTimeField(write_only=True)
    end = serializers.DateTimeField(write_only=True)

    class Meta(OrderSerializerBase.Meta):
        fields = ('order_lines', 'price', 'begin', 'end')

    def get_price(self, obj):
        return str(sum(calculate_in_memory_order_line_price(ol, obj._begin, obj._end) for ol in obj._order_lines))


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
        begin = order_data.pop('begin')
        end = order_data.pop('end')
        order = Order(**order_data)
        order_lines = [OrderLine(order=order, **data) for data in order_lines_data]

        # store the OrderLine objects and begin and end times in the Order
        # object so that we can use those when calculating prices
        order._order_lines = order_lines
        order._begin = begin
        order._end = end

        # serialize the in-memory objects
        read_serializer = PriceEndpointOrderSerializer(order)
        order_data = read_serializer.data
        order_data['order_lines'] = [PriceEndpointOrderLineSerializer(ol).data for ol in order_lines]
        order_data.update({'begin': begin, 'end': end})

        return Response(order_data, status=200)


class ResourceProductSerializer(TranslatedModelSerializer):
    class Meta:
        model = Product
        fields = ('id', 'name', 'type', 'pretax_price', 'price_type', 'tax_percentage')


register_view(OrderViewSet, 'order')


def calculate_in_memory_order_line_price(order_line, begin, end):
    return order_line.product.get_price_for_time_range(begin, end) * order_line.quantity
