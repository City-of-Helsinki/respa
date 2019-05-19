from django.contrib import admin
from django_admin_json_editor.admin import JSONEditorWidget

from .models import AccessControlResource, AccessControlSystem


@admin.register(AccessControlSystem)
class AccessControlSystemAdmin(admin.ModelAdmin):
    def get_form(self, request, obj=None, **kwargs):
        schema = {}
        if obj is not None:
            schema = obj.get_system_config_schema()
        widget = JSONEditorWidget(schema, collapsed=False)
        form = super().get_form(request, obj, widgets={'driver_config': widget}, **kwargs)
        return form


@admin.register(AccessControlResource)
class AccessControlResourceAdmin(admin.ModelAdmin):
    list_display = ('resource', 'system', 'driver_identifier', 'active_grant_count')

    def get_form(self, request, obj=None, **kwargs):
        schema = {}
        if obj is not None:
            schema = obj.system.get_resource_config_schema()
        widget = JSONEditorWidget(schema, collapsed=False)
        form = super().get_form(request, obj, widgets={'driver_config': widget}, **kwargs)
        return form
