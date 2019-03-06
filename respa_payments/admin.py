from django.contrib import admin
from respa_payments.models import Sku, Order

class OrderAdmin(admin.ModelAdmin):
    raw_id_fields = ('reservation', 'created_by', 'modified_by',)

admin.site.register(Sku)
admin.site.register(Order, OrderAdmin)
