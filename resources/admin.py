from modeltranslation.admin import TranslationAdmin
from django.contrib import admin
from .models import Resource, Reservation, ResourceType, Period, Day, Unit

from django.contrib.admin import AdminSite
from django.utils.translation import ugettext_lazy


class RespaAdminSite(AdminSite):
    # Text to put at the end of each page's <title>.
    site_title = ugettext_lazy('RESPA Resource booking system')

    # Text to put in each page's <h1>.
    site_header = ugettext_lazy('RESPA Resource booking system')

    # Text to put at the top of the admin index page.
    index_title = ugettext_lazy('RESPA Administration')

admin_site = RespaAdminSite()


class PeriodInline(admin.TabularInline):
    model = Period


class DayInline(admin.TabularInline):
    model = Day


class ResourceAdmin(admin.ModelAdmin):
    inlines = [
        PeriodInline
    ]


class UnitAdmin(TranslationAdmin):
    inlines = [
        PeriodInline
    ]


admin_site.register(Resource, ResourceAdmin)
admin_site.register(Reservation)
admin_site.register(ResourceType)
admin_site.register(Day)
admin_site.register(Unit, UnitAdmin)

