from django.contrib import admin
from django.contrib.admin import site as admin_site
from django.contrib.gis import admin as geo_admin
from image_cropping import ImageCroppingMixin
from modeltranslation.admin import TranslationAdmin, TranslationStackedInline
from .base import CommonExcludeMixin
from resources.admin.period_inline import PeriodInline
from resources.models import Day, Reservation, Resource, ResourceImage, ResourceType, Unit
from resources.models import Equipment, ResourceEquipment, EquipmentAlias, EquipmentCategory


class DayInline(admin.TabularInline):
    model = Day


class ResourceEquipmentInline(CommonExcludeMixin, TranslationStackedInline):
    model = ResourceEquipment
    fields = ('equipment', 'description', 'data')
    extra = 1


class ResourceAdmin(CommonExcludeMixin, TranslationAdmin, geo_admin.OSMGeoAdmin):
    inlines = [
        PeriodInline,
        ResourceEquipmentInline,
    ]

    default_lon = 2776460  # Central Railway Station in EPSG:3857
    default_lat = 8438120
    default_zoom = 12


class UnitAdmin(CommonExcludeMixin, TranslationAdmin, geo_admin.OSMGeoAdmin):
    inlines = [
        PeriodInline
    ]

    default_lon = 2776460  # Central Railway Station in EPSG:3857
    default_lat = 8438120
    default_zoom = 12


class ResourceImageAdmin(CommonExcludeMixin, ImageCroppingMixin, TranslationAdmin):
    exclude = ('sort_order', 'image_format')


class EquipmentAliasInline(CommonExcludeMixin, admin.TabularInline):
    model = EquipmentAlias
    readonly_fields = ()
    exclude = CommonExcludeMixin.exclude + ('id',)
    extra = 1


class EquipmentAdmin(CommonExcludeMixin, TranslationAdmin):
    inlines = (
        EquipmentAliasInline,
    )


class ResourceEquipmentAdmin(CommonExcludeMixin, TranslationAdmin):
    fields = ('resource', 'equipment', 'description', 'data')


class ReservationAdmin(CommonExcludeMixin, admin.ModelAdmin):
    pass


class ResourceTypeAdmin(CommonExcludeMixin, TranslationAdmin):
    pass


class EquipmentCategoryAdmin(TranslationAdmin):
    pass


admin_site.register(ResourceImage, ResourceImageAdmin)
admin_site.register(Resource, ResourceAdmin)
admin_site.register(Reservation, ReservationAdmin)
admin_site.register(ResourceType, ResourceTypeAdmin)
admin_site.register(Day)
admin_site.register(Unit, UnitAdmin)
admin_site.register(Equipment, EquipmentAdmin)
admin_site.register(ResourceEquipment, ResourceEquipmentAdmin)
admin_site.register(EquipmentCategory, EquipmentCategoryAdmin)
