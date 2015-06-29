from modeltranslation.admin import TranslationAdmin
from django.contrib import admin
from .models import Resource, Reservation, ResourceType, Period, Day, Unit


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


admin.site.register(Resource, ResourceAdmin)
admin.site.register(Reservation)
admin.site.register(ResourceType)
admin.site.register(Day)
admin.site.register(Unit, UnitAdmin)
