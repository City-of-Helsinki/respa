from django.conf import settings
from django.contrib import admin
from django.utils.timezone import localtime
from django.utils.translation import ugettext_lazy as _
from modeltranslation.admin import TranslationAdmin

from .models import Order, OrderLine, OrderLogEntry, Product


def get_datetime_in_localtime(dt):
    if not dt:
        return None
    return localtime(dt).strftime('%d %b %Y %H:%M:%S')


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
    can_delete = False

    def has_add_permission(self, request, obj):
        return False

    def price(self, obj):
        return obj.get_price()

    price.short_description = _('price')


class OrderLogEntryInline(admin.TabularInline):
    model = OrderLogEntry
    extra = 0
    readonly_fields = ('timestamp_with_seconds', 'state_change', 'message')
    can_delete = False

    def has_add_permission(self, request, obj):
        return False

    def timestamp_with_seconds(self, obj):
        return get_datetime_in_localtime(obj.timestamp)

    timestamp_with_seconds.short_description = _('timestamp')


class OrderAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'state', 'reservation', 'order_number', 'price')
    raw_id_fields = ('reservation',)
    inlines = (OrderLineInline, OrderLogEntryInline)
    ordering = ('-id',)

    actions = None

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields if f.name != 'id'] + ['price']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        if obj and obj.state == Order.CONFIRMED:
            return True
        return False

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_save_and_continue'] = False
        extra_context['show_save'] = False
        return super().changeform_view(request, object_id, extra_context=extra_context)

    def delete_model(self, request, obj):
        obj.set_state(Order.CANCELLED)

    def price(self, obj):
        return obj.get_price()

    price.short_description = _('price')

    def created_at(self, obj):
        return get_datetime_in_localtime(obj.created_at)

    created_at.short_description = _('created at')


if settings.RESPA_PAYMENTS_ENABLED:
    admin.site.register(Product, ProductAdmin)
    admin.site.register(Order, OrderAdmin)
