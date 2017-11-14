import io

from django.utils.translation import pgettext_lazy, ugettext_lazy as _
from django.utils import formats
from django.utils.timezone import localtime
from rest_framework import exceptions, serializers

from caterings.models import CateringOrder
from resources.models import Reservation
from .base import BaseReport, DocxRenderer


class ReservationDetailsSerializer(serializers.Serializer):
    reservation = serializers.IntegerField()

    def validate_reservation(self, value):
        try:
            reservation = Reservation.objects.get(id=value)
        except Reservation.DoesNotExist:
            raise exceptions.ValidationError(
               serializers.PrimaryKeyRelatedField.default_error_messages.get('does_not_exist').format(pk_value=value)
            )
        return reservation


class ReservationDetailsDocxRenderer(DocxRenderer):
    def render(self, data, media_type=None, renderer_context=None):
        reservation = data['reservation']
        user = renderer_context['request'].user
        document = self.create_document()

        begin_date = formats.date_format(reservation.begin.date())
        begin_time = formats.time_format(localtime(reservation.begin))
        end_date = formats.date_format(reservation.end.date())
        end_time = formats.time_format(localtime(reservation.end))
        end_str = '%s' % end_time if begin_date == end_date else '%s %s' % (end_date, end_time)
        place_str = '%s / %s' % (reservation.resource.unit.name, reservation.resource.name)
        time_str = '%s %s %s–%s' % (begin_date, pgettext_lazy('time', 'at'), begin_time, end_str)

        document.add_heading(place_str, 1)
        document.add_heading(time_str, 2)
        document.add_heading(_('Basic information'), 2)

        # collect attributes from the reservation, skip empty ones
        attrs = [(field, getattr(reservation, field)) for field in (
            'reserver_name',
            'reserver_phone_number',
            'event_subject',
            'host_name',
            'number_of_participants',
            'participants',
        ) if getattr(reservation, field) and reservation.can_view_field(user, field)]

        if attrs:
            table = document.add_table(rows=0, cols=2)

            for attr in attrs:
                row_cells = table.add_row().cells
                row_cells[0].text = Reservation._meta.get_field(attr[0]).verbose_name + ':'
                row_cells[1].text = str(attr[1])
        else:
            document.add_paragraph(_('No information available'))

        document.add_heading(pgettext_lazy('report', 'Catering order'), 2)

        if not reservation.can_view_catering_orders(user):
            document.add_paragraph(_('No information available'))
        else:
            # TODO for now assume there isn't more than one catering order per reservation
            try:
                catering_order = reservation.catering_orders.last()
            except CateringOrder.DoesNotExist:
                catering_order = None

            if catering_order:
                table = document.add_table(rows=0, cols=2)

                for order_line in catering_order.order_lines.all():
                    row_cells = table.add_row().cells
                    row_cells[0].text = order_line.product.name
                    row_cells[1].text = '%s %s' % (str(order_line.quantity), _('pcs.'))

                row_cells = table.add_row().cells
                row_cells[0].text = _('Invoicing data')
                row_cells[1].text = catering_order.invoicing_data

                if catering_order.message:
                    row_cells = table.add_row().cells
                    row_cells[0].text = _('Message')
                    row_cells[1].text = catering_order.message
            else:
                document.add_paragraph(_('No catering order'))

        output = io.BytesIO()
        document.save(output)

        return output.getvalue()


class ReservationDetailsReport(BaseReport):
    serializer_class = ReservationDetailsSerializer
    renderer_classes = (ReservationDetailsDocxRenderer,)

    def get_filename(self, request, validated_data):
        return '%s-%s.docx' % (_('reservation-details'), validated_data['reservation'].id)
