from django.contrib.admin import ModelAdmin, site
from django.forms.widgets import PasswordInput

from respa_exchange.models import ExchangeConfiguration, ExchangeReservation, ExchangeResource


class ExchangeResourceAdmin(ModelAdmin):
    list_display = ('resource', 'sync_from_respa', 'sync_to_respa', 'principal_email')
    list_filter = ('sync_from_respa', 'sync_to_respa')
    search_fields = ('resource__name', 'principal_email')
    raw_id_fields = ('resource',)


class ExchangeReservationAdmin(ModelAdmin):
    readonly_fields = [f.attname for f in ExchangeReservation._meta.get_fields()]

    def has_add_permission(self, request):
        return False  # pragma: no cover

    def has_delete_permission(self, request, obj=None):
        return False  # pragma: no cover


class ExchangeConfigurationAdmin(ModelAdmin):
    list_display = ('name', 'url', 'enabled')
    list_filter = ('enabled',)
    search_fields = ('name', 'url')

    def get_form(self, request, obj=None, **kwargs):  # pragma: no cover
        form = super(ExchangeConfigurationAdmin, self).get_form(request, obj, **kwargs)
        form.base_fields["password"].widget = PasswordInput(render_value=True)
        return form


site.register(ExchangeReservation, ExchangeReservationAdmin)
site.register(ExchangeResource, ExchangeResourceAdmin)
site.register(ExchangeConfiguration, ExchangeConfigurationAdmin)
