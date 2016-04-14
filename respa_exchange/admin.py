from django.contrib.admin import ModelAdmin, site

from respa_exchange.models import ExchangeReservation, ExchangeResource


class ExchangeResourceAdmin(ModelAdmin):
    list_display = ('resource', 'sync_from_respa', 'sync_to_respa', 'principal_email')
    list_filter = ('sync_from_respa', 'sync_to_respa')
    search_fields = ('resource__name', 'principal_email')
    raw_id_fields = ('resource',)


class ExchangeReservationAdmin(ModelAdmin):
    readonly_fields = [f.attname for f in ExchangeReservation._meta.get_fields()]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


site.register(ExchangeReservation, ExchangeReservationAdmin)
site.register(ExchangeResource, ExchangeResourceAdmin)
