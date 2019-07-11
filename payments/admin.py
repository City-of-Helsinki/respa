from django.conf import settings
from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.timezone import localtime
from django.utils.translation import ugettext_lazy as _
from modeltranslation.admin import TranslationAdmin

from .models import Order, OrderLine, OrderLogEntry, Product


def get_datetime_in_localtime(dt):
    if not dt:
        return None
    return localtime(dt).strftime('%d %b %Y %H:%M:%S')


class ProductAdmin(TranslationAdmin):
    list_display = (
        'product_id', 'sku', 'name', 'type', 'price', 'price_type', 'tax_percentage', 'get_pretax_price',
        'max_quantity', 'get_resources', 'get_created_at', 'get_modified_at'
    )
    readonly_fields = ('product_id',)
    fieldsets = (
        (None, {
            'fields': ('sku', 'type', 'name', 'description', 'max_quantity')
        }),
        (_('price').capitalize(), {
            'fields': ('price', 'price_type', 'tax_percentage'),
        }),
        ('resources'.capitalize(), {
            'fields': ('resources',)
        }),
    )
    ordering = ('-product_id',)

    def get_pretax_price(self, obj):
        return obj.get_pretax_price()

    get_pretax_price.short_description = _('price excluding VAT')

    def get_resources(self, obj):
        return mark_safe('<br>'.join([str(r) for r in obj.resources.all()]))

    get_resources.short_description = _('resources')

    def get_created_at(self, obj):
        return Product.objects.filter(product_id=obj.product_id).first().created_at

    get_created_at.short_description = _('created at')

    def get_modified_at(self, obj):
        return obj.created_at

    get_modified_at.short_description = _('modified at')

    def get_queryset(self, request):
        return super().get_queryset(request).current()

    def change_view(self, request, object_id, form_url='', extra_context=None):
        # disable "save and continue editing" button since it does not work
        # because of the Product versioning stuff
        extra_context = extra_context or {}
        extra_context['show_save_and_continue'] = False
        return super().change_view(request, object_id, form_url, extra_context=extra_context)


class OrderLineInline(admin.TabularInline):
    model = OrderLine
    fields = (
        'product', 'product_type', 'unit_price', 'quantity', 'price', 'tax_percentage', 'tax_amount', 'pretax_price'
    )
    extra = 0
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj):
        return False

    def product_type(self, obj):
        return obj.product.type

    product_type.short_description = _('product type')

    def price(self, obj):
        return obj.get_price()

    price.short_description = _('price including VAT')

    def unit_price(self, obj):
        return obj.get_unit_price()

    unit_price.short_description = _('unit price')

    def tax_percentage(self, obj):
        return obj.product.tax_percentage

    tax_percentage.short_description = _('tax percentage')

    def tax_amount(self, obj):
        return obj.get_tax_amount()

    tax_amount.short_description = _('tax amount')

    def pretax_price(self, obj):
        return obj.get_pretax_price()

    pretax_price.short_description = _('price excluding VAT')


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
    list_display = ('order_number', 'user', 'created_at', 'state', 'reservation', 'price', 'tax_amount', 'pretax_price')

    fieldsets = (
        (None, {
            'fields': ('order_number', 'created_at', 'state', 'reservation', 'user')
        }),
        (_('total price').capitalize(), {
            'fields': (('price', 'tax_amount', 'pretax_price'),)
        })
    )

    raw_id_fields = ('reservation',)
    inlines = (OrderLineInline, OrderLogEntryInline)
    ordering = ('-id',)
    search_fields = ('order_number',)
    list_filter = ('state',)

    actions = None

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields if f.name != 'id'] + [
            'user', 'created_at', 'price', 'tax_amount', 'pretax_price'
        ]

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
        obj.set_state(Order.CANCELLED, log_message='Cancelled using the Django admin UI.')

    def user(self, obj):
        return obj.reservation.user

    user.short_description = _('user')

    def price(self, obj):
        return obj.get_price()

    price.short_description = _('price including VAT')

    def created_at(self, obj):
        return get_datetime_in_localtime(obj.created_at)

    created_at.short_description = _('created at')

    def tax_amount(self, obj):
        return obj.get_tax_amount()

    tax_amount.short_description = _('tax amount')

    def pretax_price(self, obj):
        return obj.get_pretax_price()

    pretax_price.short_description = _('price excluding VAT')


if settings.RESPA_PAYMENTS_ENABLED:
    admin.site.register(Product, ProductAdmin)
    admin.site.register(Order, OrderAdmin)
