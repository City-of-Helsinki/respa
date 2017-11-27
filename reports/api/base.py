from django.conf import settings
from docx import Document
from rest_framework import renderers, generics
from rest_framework.response import Response
from rest_framework.settings import api_settings


class BaseReport(generics.GenericAPIView):
    """
    Base view for reports.

    To create a new report override this class and implement:
        - Serializer that validates possible query params and provides
          data needed to build the report
        - Renderer(s) that generates the actual report based on the data from the serializer
        - optional: provide a filename for the report by overriding get_filename()
    """
    serializer_class = None
    renderer_classes = None

    def get_filename(self, request, validated_data):
        return None

    def get(self, request, format=None):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        response = Response(serializer.data)

        filename = self.get_filename(request, serializer.data)
        if filename:
            response['Content-Disposition'] = 'attachment; filename=%s' % filename
        return response

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)

        # use the first renderer from settings to display errors
        if response.status_code != 200:
            first_renderer = api_settings.DEFAULT_RENDERER_CLASSES[0]()
            response.accepted_renderer = first_renderer
            response.accepted_media_type = first_renderer.media_type

        return response


class DocxRenderer(renderers.BaseRenderer):
    media_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    format = 'docx'
    charset = None
    render_style = 'binary'

    @staticmethod
    def create_document():
        base_template = getattr(settings, 'RESPA_DOCX_TEMPLATE', None)
        return Document(base_template) if base_template else Document()
