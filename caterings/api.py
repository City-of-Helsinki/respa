from django.db import transaction

import django_filters
from rest_framework import exceptions, serializers, viewsets

from resources.api.base import NullableDateTimeField, TranslatedModelSerializer, register_view

from .models import CateringProduct, CateringProductCategory, CateringOrder, CateringOrderLine, CateringProvider


class CateringProviderSerializer(TranslatedModelSerializer):
    class Meta:
        model = CateringProvider
        fields = ('id', 'name', 'price_list_url', 'units')


class CateringProviderFilter(django_filters.rest_framework.FilterSet):
    unit = django_filters.CharFilter(name='units')

    class Meta:
        model = CateringProvider
        fields = ('unit',)


class CateringProvider(viewsets.ReadOnlyModelViewSet):
    queryset = CateringProvider.objects.prefetch_related('units')
    serializer_class = CateringProviderSerializer
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,)
    filter_class = CateringProviderFilter

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
    filter_class = CateringProductCategoryFilter

register_view(CateringProductCategoryViewSet, 'catering_product_category')


class CateringProductSerializer(TranslatedModelSerializer):
    class Meta:
        model = CateringProduct
        fields = ('id', 'name', 'category', 'description')


class CateringProductFilter(django_filters.rest_framework.FilterSet):
    provider = django_filters.NumberFilter(name='category__provider')

    class Meta:
        model = CateringProduct
        fields = ('provider', 'category')


class CateringProductViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CateringProduct.objects.all()
    serializer_class = CateringProductSerializer
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,)
    filter_class = CateringProductFilter

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
        fields = ('id', 'created_at', 'modified_at', 'reservation', 'order_lines', 'invoicing_data', 'message')

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

    def validate(self, validated_data):
        reservation = validated_data.get('reservation') or self.instance.reservation
        if reservation and reservation.user != self.context['request'].user:
            raise exceptions.PermissionDenied(_("You are not permitted to modify this reservation's catering orders."))
        return validated_data


class CateringOrderViewSet(viewsets.ModelViewSet):
    queryset = CateringOrder.objects.prefetch_related('order_lines')
    serializer_class = CateringOrderSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if not user.is_authenticated():
            return queryset.none()
        return super().get_queryset().filter(reservation__user=user)

register_view(CateringOrderViewSet, 'catering_order')
