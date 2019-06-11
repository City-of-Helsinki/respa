from django.conf import settings
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from modeltranslation.admin import TranslationAdmin

from .models import Order, OrderLine, Product


class ProductAdmin(TranslationAdmin):
    list_display = ('product_id', 'name', 'type', 'pretax_price', 'price_type', 'price')
    readonly_fields = ('product_id', 'price')

    def get_queryset(self, request):
        return super().get_queryset(request).current()

    def change_view(self, request, object_id, form_url='', extra_context=None):
        # disable "save and continue editing" button since it does not work
        # because of the Product versioning stuff
        extra_context = extra_context or {}
        extra_context['show_save_and_continue'] = False
        return super().change_view(request, object_id, form_url, extra_context=extra_context)

    def price(self, obj):
        if not obj.id:
            return None
        return obj.get_price()

    price.short_description = _('price')


class OrderLineInline(admin.TabularInline):
    model = OrderLine
    extra = 0
    readonly_fields = ('price',)

    def price(self, obj):
        return obj.get_price()

    price.short_description = _('price')


class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'reservation', 'price')
    raw_id_fields = ('reservation',)
    inlines = (OrderLineInline,)
    readonly_fields = ('price',)
    ordering = ('-id',)

    def price(self, obj):
        return obj.get_price()

    price.short_description = _('price')


if settings.RESPA_PAYMENTS_ENABLED:
    admin.site.register(Product, ProductAdmin)
    admin.site.register(Order, OrderAdmin)
