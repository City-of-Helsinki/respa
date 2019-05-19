import io

from django.utils.translation import get_language, pgettext_lazy, ugettext_lazy as _
from django.utils import formats
from django.utils.timezone import localtime
from rest_framework import exceptions, serializers
from docx.shared import Cm

from caterings.models import CateringOrder
from resources.models import Reservation, Resource
from resources.models.utils import format_dt_range
from resources.api.reservation import ReservationSerializer, ReservationViewSet, ReservationCacheMixin
from .base import BaseReport, DocxRenderer
from .utils import iso_to_dt


class ReservationDetailsDocxRenderer(DocxRenderer):
    def render_one(self, document, reservation, renderer_context):
        begin = localtime(iso_to_dt(reservation['begin']))
        end = localtime(iso_to_dt(reservation['end']))

        resource = self.resources[reservation['resource']]
        time_str = format_dt_range(get_language(), begin, end)

        document.add_heading(resource.name, 1)
        document.add_heading(resource.unit.name, 3)
        time_paragraph = document.add_heading(time_str, 2)
        time_paragraph.paragraph_format.space_before = Cm(1)

        # collect attributes from the reservation, skip empty ones
        attrs = [(field, reservation.get(field)) for field in (
            'event_subject',
            'reserver_name',
            'reserver_phone_number',
            'host_name',
            'event_description',
            'number_of_participants',
            'participants',
        ) if reservation.get(field)]

        if attrs:
            table = document.add_table(rows=0, cols=2)

            for attr in attrs:
                row_cells = table.add_row().cells
                row_cells[0].text = Reservation._meta.get_field(attr[0]).verbose_name + ':'
                row_cells[1].text = str(attr[1])
        else:
            document.add_paragraph(_('No information available'))

        # 'has_catering_order' is only set if the user has permission to view
        # the catering orders
        if reservation.get('has_catering_order'):
            catering_order = self.catering_orders[reservation['id']]
            document.add_heading(pgettext_lazy('report', 'Catering order'), 2)

            table = document.add_table(rows=0, cols=2)

            for order_line in catering_order.order_lines.all():
                row_cells = table.add_row().cells
                row_cells[0].text = order_line.product.name
                row_cells[1].text = '%s %s' % (str(order_line.quantity), _('pcs.'))

            if catering_order.message:
                row_cells = table.add_row().cells
                row_cells[0].text = _('Message')
                row_cells[1].text = catering_order.message

            row_cells = table.add_row().cells
            row_cells[0].text = _('Invoicing data')
            row_cells[1].text = catering_order.invoicing_data

    def render(self, data, media_type=None, renderer_context=None):
        document = self.create_document()

        # Prefetch some objects
        resource_ids = [rv['resource'] for rv in data]
        self.resources = {x.id: x for x in Resource.objects.filter(id__in=resource_ids).select_related('unit')}
        catering_rv_ids = [rv['id'] for rv in data if rv.get('has_catering_order')]
        catering_qs = CateringOrder.objects.filter(reservation__in=catering_rv_ids).prefetch_related('order_lines')\
            .prefetch_related('order_lines__product')
        self.catering_orders = {x.reservation_id: x for x in catering_qs}

        for idx, rv in enumerate(data):
            if idx != 0:
                document.add_page_break()
            self.render_one(document, rv, renderer_context)

        output = io.BytesIO()
        document.save(output)

        return output.getvalue()


class ReservationDetailsReport(BaseReport, ReservationCacheMixin):
    queryset = ReservationViewSet.queryset.current()
    serializer_class = ReservationSerializer
    renderer_classes = (ReservationDetailsDocxRenderer,)
    filter_backends = ReservationViewSet.filter_backends
    filterset_class = ReservationViewSet.filterset_class

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

    def get_filename(self, request, data):
        return '%s.docx' % (_('reservation-details'),)
