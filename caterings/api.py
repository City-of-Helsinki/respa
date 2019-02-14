from django.db import transaction
from django.utils.translation import gettext_lazy as _

import django_filters
import reversion
from rest_framework import exceptions, serializers, viewsets

from resources.api.base import NullableDateTimeField, TranslatedModelSerializer, register_view

from .models import CateringProduct, CateringProductCategory, CateringOrder, CateringOrderLine, CateringProvider


class CateringProviderSerializer(TranslatedModelSerializer):
    class Meta:
        model = CateringProvider
        fields = ('id', 'name', 'price_list_url', 'units')


class CateringProviderFilter(django_filters.rest_framework.FilterSet):
    unit = django_filters.CharFilter(field_name='units')

    class Meta:
        model = CateringProvider
        fields = ('unit',)


class CateringProvider(viewsets.ReadOnlyModelViewSet):
    queryset = CateringProvider.objects.prefetch_related('units')
    serializer_class = CateringProviderSerializer
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,)
    filterset_class = CateringProviderFilter

register_view(CateringProvider, 'catering_provider')


class CateringProductCategorySerializer(TranslatedModelSerializer):
    class Meta:
        model = CateringProductCategory
        fields = ('id', 'name', 'products', 'provider')


class CateringProductCategoryFilter(django_filters.rest_framework.FilterSet):
    class Meta:
        model = CateringProductCategory
        fields = ('provider',)


class CateringProductCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CateringProductCategory.objects.prefetch_related('products')
    serializer_class = CateringProductCategorySerializer
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,)
    filterset_class = CateringProductCategoryFilter

register_view(CateringProductCategoryViewSet, 'catering_product_category')


class CateringProductSerializer(TranslatedModelSerializer):
    class Meta:
        model = CateringProduct
        fields = ('id', 'name', 'category', 'description')


class CateringProductFilter(django_filters.rest_framework.FilterSet):
    provider = django_filters.NumberFilter(field_name='category__provider')

    class Meta:
        model = CateringProduct
        fields = ('provider', 'category')


class CateringProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CateringProduct.objects.all()
    serializer_class = CateringProductSerializer
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,)
    filterset_class = CateringProductFilter

register_view(CateringProductViewSet, 'catering_product')


# taken from https://github.com/encode/django-rest-framework/issues/3847
# needed because product field must be required always, also with PATCH
class MonkeyPatchPartial:
    """
    Work around bug #3847 in djangorestframework by monkey-patching the partial
    attribute of the root serializer during the call to validate_empty_values.
    """

    def __init__(self, root):
        self._root = root

    def __enter__(self):
        self._old = getattr(self._root, 'partial')
        setattr(self._root, 'partial', False)

    def __exit__(self, *args):
        setattr(self._root, 'partial', self._old)


class CateringOrderLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = CateringOrderLine
        fields = ('product', 'quantity')

    def run_validation(self, *args, **kwargs):
        with MonkeyPatchPartial(self.root):
            return super().run_validation(*args, **kwargs)


class CateringOrderSerializer(serializers.ModelSerializer):
    created_at = NullableDateTimeField(read_only=True)
    modified_at = NullableDateTimeField(read_only=True)
    order_lines = CateringOrderLineSerializer(many=True, required=True, allow_empty=False)

    class Meta:
        model = CateringOrder
        fields = (
            'id', 'created_at', 'modified_at', 'reservation', 'order_lines', 'invoicing_data', 'message',
            'serving_time',
        )

    def _handle_order_lines(self, order, order_line_data):
        order.order_lines.all().delete()
        for order_line_datum in order_line_data:
            CateringOrderLine.objects.create(order=order, **order_line_datum)

    @transaction.atomic
    def create(self, validated_data):
        order_line_data = validated_data.pop('order_lines', [])
        new_order = super().create(validated_data)
        self._handle_order_lines(new_order, order_line_data)
        return new_order

    @transaction.atomic
    def update(self, instance, validated_data):
        order_line_data = validated_data.pop('order_lines', [])
        updated_order = super().update(instance, validated_data)
        self._handle_order_lines(updated_order, order_line_data)
        return updated_order

    def to_internal_value(self, data):
        # Remove order lines with quantity == 0
        if 'order_lines' in data and isinstance(data['order_lines'], list):
            order_lines = data['order_lines']
            data['order_lines'] = [x for x in order_lines if x.get('quantity') != 0]

        return super().to_internal_value(data)

    def validate(self, validated_data):
        reservation = validated_data.get('reservation') or self.instance.reservation
        if reservation:
            resource = reservation.resource
            user = self.context['request'].user
            if reservation.user != user and not resource.can_modify_catering_orders(user):
                raise exceptions.PermissionDenied(_("No permission to modify this reservation's catering orders."))

        provider = validated_data['order_lines'][0]['product'].category.provider
        validated_data['provider'] = provider
        for order_line in validated_data['order_lines'][1:]:
            if order_line['product'].category.provider != provider:
                raise exceptions.ValidationError(_('The order contains products from several providers.'))

        if reservation.resource.unit not in provider.units.all():
            raise exceptions.ValidationError(
                "The provider isn't available in the reservation's unit."
            )

        return validated_data


class CateringOrderFilter(django_filters.rest_framework.FilterSet):
    class Meta:
        model = CateringOrder
        fields = ('reservation',)


class CateringOrderViewSet(viewsets.ModelViewSet):
    queryset = CateringOrder.objects.prefetch_related('order_lines')
    serializer_class = CateringOrderSerializer
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,)
    filterset_class = CateringOrderFilter

    def get_queryset(self):
        return super().get_queryset().can_view(self.request.user)

    def perform_create(self, serializer):
        with reversion.create_revision():
            instance = serializer.save()
            reversion.set_user(self.request.user)
            reversion.set_comment('Created using the API.')

        instance.send_created_notification(request=self.request)

    def perform_update(self, serializer):
        with reversion.create_revision():
            instance = serializer.save()
            reversion.set_user(self.request.user)
            reversion.set_comment('Updated using the API.')

        # TODO somehow check that the order is actually modified before sending the notification?
        instance.send_modified_notification(request=self.request)

    def perform_destroy(self, instance):
        instance.send_deleted_notification(request=self.request)
        super().perform_destroy(instance)


register_view(CateringOrderViewSet, 'catering_order')
