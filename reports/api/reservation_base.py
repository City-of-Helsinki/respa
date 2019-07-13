import io

from django.utils.translation import ugettext_lazy as _
from rest_framework import exceptions, serializers

from caterings.models import CateringOrder
from resources.models import Reservation, Resource
from resources.api.reservation import ReservationSerializer, ReservationViewSet, ReservationCacheMixin

from .base import DocxRenderer, BaseReport


class ReservationDocxRenderer(DocxRenderer):
    def render(self, data, media_type=None, renderer_context=None):
        document = self.create_document()

        # Prefetch some objects
        resource_ids = [rv['resource'] for rv in data]
        self.resources = {x.id: x for x in Resource.objects.filter(id__in=resource_ids).select_related('unit')}
        catering_rv_ids = [rv['id'] for rv in data if rv.get('has_catering_order')]
        catering_qs = CateringOrder.objects.filter(reservation__in=catering_rv_ids).prefetch_related('order_lines')\
            .prefetch_related('order_lines__product')
        self.catering_orders = {x.reservation_id: x for x in catering_qs}

        self.render_all(data, document, renderer_context)

        output = io.BytesIO()
        document.save(output)

        return output.getvalue()


class ReservationReport(BaseReport, ReservationCacheMixin):
    queryset = ReservationViewSet.queryset.current()
    serializer_class = ReservationSerializer
    filter_backends = ReservationViewSet.filter_backends
    filter_class = ReservationViewSet.filter_class

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        queryset = queryset.filter(resource__in=Resource.objects.visible_for(user))
        return queryset

    def get_serializer(self, *args, **kwargs):
        if 'data' not in kwargs and len(args) == 1:
            # It's a read operation
            instance_or_page = args[0]
            if isinstance(instance_or_page, Reservation):
                self._page = [instance_or_page]
            else:
                self._page = instance_or_page

        return super().get_serializer(*args, **kwargs)

    def get_serializer_context(self, *args, **kwargs):
        context = super().get_serializer_context()
        if not hasattr(self, '_page'):
            return context
        context.update(self._get_cache_context())
        return context

    def filter_queryset(self, queryset):
        params = self.request.query_params
        reservation_id = params.get('reservation')
        if reservation_id:
            try:
                Reservation.objects.get(id=reservation_id)
            except Reservation.DoesNotExist:
                raise exceptions.NotFound(
                   serializers.PrimaryKeyRelatedField.default_error_messages.get('does_not_exist').format(pk_value=reservation_id)
                )
            queryset = queryset.filter(id=reservation_id)
        else:
            queryset = super().filter_queryset(queryset)

        if queryset.count() > 1000:
            raise exceptions.NotAcceptable(_("Too many (> 1000) reservations to return"))

        return queryset
