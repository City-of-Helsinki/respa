import datetime
import io

from django.utils.translation import ugettext_lazy as _
from django.utils import formats
from django.utils.timezone import localtime
from rest_framework import exceptions, renderers, serializers, status, views
from rest_framework.response import Response
from rest_framework.settings import api_settings
from docx import Document
from docx.shared import Pt

from resources.models import Reservation, Resource, Unit


class DocxRenderer(renderers.BaseRenderer):
    media_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    format = 'docx'
    charset = None
    render_style = 'binary'

    def render(self, data, media_type=None, renderer_context=None):
        day = data['day']
        resource_qs = data['resource_qs']

        include_resources_without_reservations = data['include_resources_without_reservations']
        document = Document()

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

            name_h = document.add_heading(resource.name, 1)
            name_h.paragraph_format.space_after = Pt(12)
            date_h = document.add_heading(formats.date_format(day, format='D j.n.Y'), 2)
            date_h.paragraph_format.space_after = Pt(48)

            if reservation_count == 0:
                p = document.add_paragraph(_('No reservations'))
                p.paragraph_format.space_before = Pt(24)

            for reservation in reservations:

                # the time
                p = document.add_paragraph()
                p.paragraph_format.space_before = Pt(24)
                p.add_run(formats.time_format(localtime(reservation.begin)) + '–' +
                          formats.time_format(localtime(reservation.end))).bold = True

                # collect attributes from the reservation, skip empty ones
                attrs = [(field, getattr(reservation, field)) for field in (
                    'event_subject',
                    'reserver_name',
                    'host_name',
                    'number_of_participants',
                ) if getattr(reservation, field)]

                if not attrs:
                    # this should not normally happen as event_subject and number_of_participants
                    # should be required fields
                    p = document.add_paragraph(_('No information available'))
                    p.paragraph_format.space_before = Pt(24)
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


class ReportParamSerializer(serializers.Serializer):
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


class DailyReservationsReport(views.APIView):
    renderer_classes = (DocxRenderer,)

    def get(self, request, format=None):
        serializer = ReportParamSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(
                data=serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        response = Response(serializer.validated_data)

        filename = '%s-%s' % (_('day-report'), serializer.validated_data['day'])
        response['Content-Disposition'] = 'attachment; filename=%s.%s' % (filename, request.accepted_renderer.format)
        return response

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)

        # use the first renderer from settings to display errors
        if response.status_code != 200:
            first_renderer = api_settings.DEFAULT_RENDERER_CLASSES[0]()
            response.accepted_renderer = first_renderer
            response.accepted_media_type = first_renderer.media_type

        return response
