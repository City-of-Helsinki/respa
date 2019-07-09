from rest_framework import mixins, permissions, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from resources.api.base import register_view

from ..api.base import OrderLineSerializerBase, OrderSerializerBase
from ..models import Order, OrderLine


class PriceEndpointOrderLineSerializer(OrderLineSerializerBase):
    def get_price(self, obj):
        return str(calculate_in_memory_order_line_price(obj, obj.order._begin, obj.order._end))


class OrderSerializer(OrderSerializerBase):
    id = serializers.ReadOnlyField(source='order_number')

    class Meta(OrderSerializerBase.Meta):
        fields = OrderSerializerBase.Meta.fields + ('id', 'reservation')


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
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    lookup_field = 'order_number'

    def get_queryset(self):
        return super().get_queryset().can_view(self.request.user)

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


register_view(OrderViewSet, 'order')


def calculate_in_memory_order_line_price(order_line, begin, end):
    return order_line.product.get_price_for_time_range(begin, end) * order_line.quantity
