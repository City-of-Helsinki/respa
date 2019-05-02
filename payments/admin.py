from django.contrib import admin
from modeltranslation.admin import TranslationAdmin

from payments.models import Order, OrderLine, Product


@admin.register(Product)
class Product(TranslationAdmin):
    list_display = ('product_id', 'name', 'type', 'pretax_price', 'price_type')
    readonly_fields = ('product_id',)

    def get_queryset(self, request):
        return super().get_queryset(request).current()

    def change_view(self, request, object_id, form_url='', extra_context=None):
        # disable "save and continue editing" button since it does not work
        # because of the Product versioning stuff
        extra_context = extra_context or {}
        extra_context['show_save_and_continue'] = False
        return super().change_view(request, object_id, form_url, extra_context=extra_context)


class OrderLineInline(admin.StackedInline):
    model = OrderLine
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    raw_id_fields = ('reservation',)
    inlines = (OrderLineInline,)
