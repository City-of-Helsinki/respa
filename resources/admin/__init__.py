from django.contrib import admin
from django.contrib.admin import site as admin_site
from django.contrib.gis import admin as geo_admin
from image_cropping import ImageCroppingMixin
from modeltranslation.admin import TranslationAdmin
from resources.admin.period_inline import PeriodInline
from resources.models import Day, Reservation, Resource, ResourceImage, ResourceType, Unit


class DayInline(admin.TabularInline):
    model = Day


class ResourceAdmin(TranslationAdmin, geo_admin.OSMGeoAdmin):
    inlines = [
        PeriodInline
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


admin_site.register(ResourceImage, ResourceImageAdmin)
admin_site.register(Resource, ResourceAdmin)
admin_site.register(Reservation)
admin_site.register(ResourceType)
admin_site.register(Day)
admin_site.register(Unit, UnitAdmin)
