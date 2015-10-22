from django.contrib import admin
from django.contrib.admin import site as admin_site
from django.contrib.gis import admin as geo_admin
from django.utils.translation import ugettext_lazy
from image_cropping import ImageCroppingMixin
from modeltranslation.admin import TranslationAdmin, TranslationInlineModelAdmin

from .models import Day, Period, Reservation, Resource, ResourceImage, ResourceType, Unit

# Text to put at the end of each page's <title>.
admin_site.site_title = ugettext_lazy('RESPA Resource booking system')

# Text to put in each page's <h1>.
admin_site.site_header = ugettext_lazy('RESPA Resource booking system')

# Text to put at the top of the admin index page.
admin_site.index_title = ugettext_lazy('RESPA Administration')


class PeriodInline(admin.TabularInline):
    model = Period


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
