from django.utils.translation import ugettext_lazy as _
from rest_framework import exceptions, mixins, permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from payments.exceptions import (
    DuplicateOrderError, PayloadValidationError, RespaPaymentError, ServiceUnavailableError, UnknownReturnCodeError
)
from payments.models import Order, OrderLine, Product
from resources.api.base import TranslatedModelSerializer, register_view
from resources.models import Reservation

from .providers import get_payment_provider


class ProductSerializer(TranslatedModelSerializer):
    id = serializers.CharField(source='product_id')
    price = serializers.CharField(source='get_price')
    tax_percentage = serializers.CharField()

    class Meta:
        model = Product
        fields = ('id', 'type', 'name', 'description', 'tax_percentage', 'price', 'price_type')


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

    def validate(self, order_line):
        if order_line.get('quantity', 1) > order_line['product'].max_quantity:
            raise serializers.ValidationError({'quantity': _('Cannot exceed max product quantity')})
        return order_line

    def validate_product(self, product):
        available_products = self.context.get('available_products')
        if available_products is not None:
            if product not in available_products:
                raise serializers.ValidationError(_("This product isn't available on the resource of the reservation."))
        return product


class OrderLineSerializer(OrderLineSerializerBase):
    def get_price(self, obj):
        return str(obj.get_price())


class PriceEndpointOrderLineSerializer(OrderLineSerializerBase):
    def get_price(self, obj):
        return str(calculate_in_memory_order_line_price(obj, obj.order._begin, obj.order._end))


class OrderSerializerBase(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='order_number')
    order_lines = OrderLineSerializer(many=True)
    price = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = (
            'id', 'state', 'reservation', 'price', 'order_lines'
        )

    def get_price(self, obj):
        return str(obj.get_price())


class OrderSerializer(OrderSerializerBase):
    return_url = serializers.CharField(write_only=True)
    payment_url = serializers.SerializerMethodField()

    class Meta(OrderSerializerBase.Meta):
        fields = OrderSerializerBase.Meta.fields + ('return_url', 'payment_url')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            reservation = Reservation.objects.get(id=self.get_initial()['reservation'])
        except (KeyError, Reservation.DoesNotExist):
            return
        self.context.update({'available_products': reservation.resource.products.current()})

    def create(self, validated_data):
        order_lines_data = validated_data.pop('order_lines', [])
        return_url = validated_data.pop('return_url', '')
        order = super().create(validated_data)

        for order_line_data in order_lines_data:
            OrderLine.objects.create(order=order, **order_line_data)

        payments = get_payment_provider()
        try:
            self.context['payment_url'] = payments.order_create(
                self.context['request'], return_url, order
            )
        except DuplicateOrderError as doe:
            raise exceptions.APIException(detail=str(doe),
                                          code=status.HTTP_409_CONFLICT)
        except (PayloadValidationError, UnknownReturnCodeError) as e:
            raise exceptions.APIException(detail=str(e),
                                          code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except ServiceUnavailableError as sue:
            raise exceptions.APIException(detail=str(sue),
                                          code=status.HTTP_503_SERVICE_UNAVAILABLE)
        except RespaPaymentError as pe:
            raise exceptions.APIException(detail=str(pe),
                                          code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return order

    def get_payment_url(self, obj):
        return self.context.get('payment_url', '')

    def validate_order_lines(self, order_lines):
        # Check order contains order lines
        if not order_lines:
            raise serializers.ValidationError(_('At least one order line required.'))

        # Check products in order lines are unique
        product_ids = [ol['product'].product_id for ol in order_lines]
        if len(product_ids) > len(set(product_ids)):
            raise serializers.ValidationError(_('Order lines cannot contain duplicate products.'))

        return order_lines

    def validate_reservation(self, reservation):
        if reservation.state != Reservation.WAITING_FOR_PAYMENT:
            raise serializers.ValidationError(
                _('Cannot create an order for a reservation that is not in state "waiting_for_payment".')
            )
        return reservation


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

    def perform_create(self, serializer):
        if not serializer.validated_data['reservation'].can_add_product_order(self.request.user):
            raise PermissionDenied()
        super().perform_create(serializer)

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
