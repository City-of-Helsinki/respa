from django.contrib import admin

from payments.models import Order, OrderLine, Product


@admin.register(Product)
class Product(admin.ModelAdmin):
    list_display = ('name', 'type', 'pretax_price', 'price_type')


class OrderLineInline(admin.StackedInline):
    model = OrderLine
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    raw_id_fields = ('reservation',)
    inlines = (OrderLineInline,)
