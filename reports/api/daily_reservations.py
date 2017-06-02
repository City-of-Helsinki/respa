import datetime
import io

from django.utils.translation import ugettext_lazy as _
from django.utils import formats
from django.utils.timezone import localtime
from rest_framework import exceptions, serializers

from resources.models import Reservation, Resource, Unit
from .base import BaseReport, DocxRenderer


class DailyReservationsSerializer(serializers.Serializer):
    day = serializers.DateField(required=False)
    unit = serializers.CharField(required=False)
    resource = serializers.CharField(required=False)
    include_resources_without_reservations = serializers.BooleanField(required=False, default=False)

    def validate_unit(self, value):
        try:
            unit = Unit.objects.get(id=value)
        except Unit.DoesNotExist:
            raise exceptions.ValidationError(
                _('Invalid pk "{pk_value}" - object does not exist.').format(pk_value=value)
            )
        return unit

    def validate_resource(self, value):
        if not value:
            return None

        resource_ids = [x.strip() for x in value.split(',')]
        resource_qs = Resource.objects.filter(id__in=resource_ids)
        return resource_qs

    def validate(self, data):
        unit = data.get('unit')
        resource_qs = data.get('resource')

        if not (unit or resource_qs):
            raise exceptions.ValidationError(_('Either unit or resource is required.'))

        if not resource_qs:
            resource_qs = unit.resources.all()
        elif unit:
            resource_qs = resource_qs.filter(unit=unit)
        data['resource_qs'] = resource_qs

        data['day'] = data.get('day', datetime.date.today())
        return data


class DailyReservationsDocxRenderer(DocxRenderer):
    def render(self, data, media_type=None, renderer_context=None):
        day = data['day']
        resource_qs = data['resource_qs']

        include_resources_without_reservations = data['include_resources_without_reservations']
        document = self.create_document()

        first_resource = True
        atleast_one_reservation = False

        for resource in resource_qs:
            reservations = Reservation.objects.filter(resource=resource, begin__date=day).order_by('resource', 'begin')
            reservation_count = reservations.count()

            if reservation_count == 0 and not include_resources_without_reservations:
                continue

            atleast_one_reservation = True

            # every resource on it's own page, a bit easier to add linebreak here than at the end
            if not first_resource:
                document.add_page_break()
            else:
                first_resource = False

            user = renderer_context['request'].user
            document.add_heading(resource.name, 1)
            document.add_heading(formats.date_format(day, format='D j.n.Y'), 2)

            if reservation_count == 0:
                document.add_paragraph(_('No reservations'))

            for reservation in reservations:

                # the time
                document.add_heading(formats.time_format(localtime(reservation.begin)) + '–' +
                                     formats.time_format(localtime(reservation.end)), 3)

                # collect attributes from the reservation, skip empty ones
                attrs = [(field, getattr(reservation, field)) for field in (
                    'event_subject',
                    'reserver_name',
                    'host_name',
                    'number_of_participants',
                ) if getattr(reservation, field) and reservation.can_view_field(user, field)]

                if not attrs:
                    document.add_paragraph(_('No information available'))
                    continue

                table = document.add_table(rows=0, cols=2)
                # build the attribute table
                for attr in attrs:
                    row_cells = table.add_row().cells
                    row_cells[0].text = Reservation._meta.get_field(attr[0]).verbose_name + ':'
                    row_cells[1].text = str(attr[1])

        if not atleast_one_reservation:
            document.add_heading(_('No reservations'), 1)

        output = io.BytesIO()
        document.save(output)

        return output.getvalue()


class DailyReservationsReport(BaseReport):
    serializer_class = DailyReservationsSerializer
    renderer_classes = (DailyReservationsDocxRenderer,)

    def get_filename(self, request, validated_data):
        return '%s-%s.docx' % (_('day-report'), validated_data['day'])
