import io

from django.utils.translation import pgettext_lazy, ugettext_lazy as _
from django.utils import formats
from django.utils.timezone import localtime
from rest_framework import exceptions, serializers

from caterings.models import CateringOrder
from resources.models import Reservation, Resource
from resources.api.reservation import ReservationSerializer, ReservationViewSet
from .base import BaseReport, DocxRenderer
from .utils import iso_to_dt


class ReservationDetailsDocxRenderer(DocxRenderer):
    def render_one(self, document, reservation, renderer_context):
        begin = localtime(iso_to_dt(reservation['begin']))
        end = localtime(iso_to_dt(reservation['end']))
        begin_date = formats.date_format(begin.date())
        begin_time = formats.time_format(begin)
        end_date = formats.date_format(end.date())
        end_time = formats.time_format(end)
        end_str = '%s' % end_time if begin_date == end_date else '%s %s' % (end_date, end_time)

        resource = Resource.objects.get(id=reservation['resource'])
        place_str = '%s / %s' % (resource.unit.name, resource.name)
        time_str = '%s %s %s–%s' % (begin_date, pgettext_lazy('time', 'at'), begin_time, end_str)

        document.add_heading(place_str, 1)
        document.add_heading(time_str, 2)
        document.add_heading(_('Basic information'), 2)

        # collect attributes from the reservation, skip empty ones
        attrs = [(field, reservation.get(field)) for field in (
            'reserver_name',
            'reserver_phone_number',
            'host_name',
            'event_subject',
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

        user = renderer_context['request'].user
        catering_order = CateringOrder.objects.filter(reservation=reservation['id']).last()
        if catering_order and resource.can_view_catering_orders(user):
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

        for idx, rv in enumerate(data):
            if idx != 0:
                document.add_page_break()
            self.render_one(document, rv, renderer_context)

        output = io.BytesIO()
        document.save(output)

        return output.getvalue()


class ReservationDetailsReport(BaseReport):
    serializer_class = ReservationSerializer
    renderer_classes = (ReservationDetailsDocxRenderer,)
    filter_backends = ReservationViewSet.filter_backends
    filter_class = ReservationViewSet.filter_class

    def get_queryset(self):
        return Reservation.objects.all().order_by('resource__unit__name', 'resource__name', 'begin')

    def get_serializer_context(self):
        context = super().get_serializer_context()
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
