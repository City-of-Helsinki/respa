from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django_admin_json_editor.admin import JSONEditorWidget

from .models import AccessControlSystem


@admin.register(AccessControlSystem)
class JSONModelAdmin(admin.ModelAdmin):
    def driver_data_schema(self, widget):
        return {
            'type': 'object',
            'title': _('Driver configuration'),
            'properties': {
                'url': {
                    'title': 'URL',
                    'type': 'string',
                }
            }
        }

    def get_form(self, request, obj=None, **kwargs):
        widget = JSONEditorWidget(self.driver_data_schema, False)
        form = super().get_form(request, obj, widgets={'driver_data': widget}, **kwargs)
        return form
