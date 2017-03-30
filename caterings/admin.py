from django.contrib import admin
from modeltranslation.admin import TranslationAdmin

from .models import CateringProduct, CateringProductCategory, CateringOrder, CateringOrderLine, CateringProvider


class CateringProviderAdmin(admin.ModelAdmin):
    pass


class CateringProductCategoryAdmin(TranslationAdmin):
    pass


class CateringProductAdmin(TranslationAdmin):
    pass


class CateringOrderLineInline(admin.TabularInline):
    model = CateringOrderLine
    extra = 0


class CateringOrderAdmin(admin.ModelAdmin):
    inlines = (CateringOrderLineInline,)


admin.site.register(CateringProvider, CateringProviderAdmin)
admin.site.register(CateringProductCategory, CateringProductCategoryAdmin)
admin.site.register(CateringProduct, CateringProductAdmin)
admin.site.register(CateringOrder, CateringOrderAdmin)
