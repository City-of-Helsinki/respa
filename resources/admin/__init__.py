from django.contrib import admin
from django.contrib.admin import site as admin_site
from django.contrib.gis import admin as geo_admin
from image_cropping import ImageCroppingMixin
from modeltranslation.admin import TranslationAdmin
from resources.admin.period_inline import PeriodInline
from resources.models import Day, Reservation, Resource, ResourceImage, ResourceType, Unit
from resources.models import Equipment, ResourceEquipment, EquipmentAlias


class DayInline(admin.TabularInline):
    model = Day


class ResourceEquipmentInline(admin.StackedInline):
    model = ResourceEquipment
    exclude = ('id', 'description')
    extra = 1


class ResourceAdmin(TranslationAdmin, geo_admin.OSMGeoAdmin):
    inlines = [
        PeriodInline,
        ResourceEquipmentInline,
    ]

    default_lon = 2776460  # Central Railway Station in EPSG:3857
    default_lat = 8438120
    default_zoom = 12


class UnitAdmin(TranslationAdmin, geo_admin.OSMGeoAdmin):
    inlines = [
        PeriodInline
    ]

    default_lon = 2776460  # Central Railway Station in EPSG:3857
    default_lat = 8438120
    default_zoom = 12


class ResourceImageAdmin(ImageCroppingMixin, TranslationAdmin):
    exclude = ('sort_order', 'image_format')


class EquipmentAliasInline(admin.TabularInline):
    model = EquipmentAlias
    fields = ('name', 'language')
    extra = 1


class EquipmentAdmin(TranslationAdmin):
    fields = ('name',)
    inlines = (
        EquipmentAliasInline,
    )


class ResourceEquipmentAdmin(TranslationAdmin):
    pass


admin_site.register(ResourceImage, ResourceImageAdmin)
admin_site.register(Resource, ResourceAdmin)
admin_site.register(Reservation)
admin_site.register(ResourceType)
admin_site.register(Day)
admin_site.register(Unit, UnitAdmin)
admin_site.register(Equipment, EquipmentAdmin)
admin_site.register(ResourceEquipment, ResourceEquipmentAdmin)
