from django.contrib import admin
from django.contrib.admin import site as admin_site
from django.contrib.auth import get_user_model
from django.contrib.gis.admin import OSMGeoAdmin
from django import forms
from guardian import admin as guardian_admin
from image_cropping import ImageCroppingMixin
from modeltranslation.admin import TranslationAdmin, TranslationStackedInline
from .base import CommonExcludeMixin, PopulateCreatedAndModifiedMixin
from resources.admin.period_inline import PeriodInline
from resources.models import Day, Reservation, Resource, ResourceImage, ResourceType, Unit, Purpose
from resources.models import Equipment, ResourceEquipment, EquipmentAlias, EquipmentCategory


class EmailChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.email


# monkey patch django-guardian user form for better UX
class UserManage(forms.Form):
    user = EmailChoiceField(queryset=get_user_model().objects.filter(is_staff=True).order_by('email'))
guardian_admin.UserManage = UserManage


class HttpsFriendlyGeoAdmin(OSMGeoAdmin):
    openlayers_url = 'https://cdnjs.cloudflare.com/ajax/libs/openlayers/2.13.1/OpenLayers.js'


class DayInline(admin.TabularInline):
    model = Day


class ResourceEquipmentInline(PopulateCreatedAndModifiedMixin, CommonExcludeMixin, TranslationStackedInline):
    model = ResourceEquipment
    fields = ('equipment', 'description', 'data')
    extra = 0


class ResourceAdmin(PopulateCreatedAndModifiedMixin, CommonExcludeMixin, TranslationAdmin, HttpsFriendlyGeoAdmin):
    inlines = [
        PeriodInline,
        ResourceEquipmentInline,
    ]

    default_lon = 2776460  # Central Railway Station in EPSG:3857
    default_lat = 8438120
    default_zoom = 12


class UnitAdmin(PopulateCreatedAndModifiedMixin, CommonExcludeMixin, guardian_admin.GuardedModelAdminMixin,
                TranslationAdmin, HttpsFriendlyGeoAdmin):
    inlines = [
        PeriodInline
    ]

    default_lon = 2776460  # Central Railway Station in EPSG:3857
    default_lat = 8438120
    default_zoom = 12


class ResourceImageAdmin(PopulateCreatedAndModifiedMixin, CommonExcludeMixin, ImageCroppingMixin, TranslationAdmin):
    exclude = ('sort_order', 'image_format')


class EquipmentAliasInline(PopulateCreatedAndModifiedMixin, CommonExcludeMixin, admin.TabularInline):
    model = EquipmentAlias
    readonly_fields = ()
    exclude = CommonExcludeMixin.exclude + ('id',)
    extra = 1


class EquipmentAdmin(PopulateCreatedAndModifiedMixin, CommonExcludeMixin, TranslationAdmin):
    inlines = (
        EquipmentAliasInline,
    )


class ResourceEquipmentAdmin(PopulateCreatedAndModifiedMixin, CommonExcludeMixin, TranslationAdmin):
    fields = ('resource', 'equipment', 'description', 'data')


class ReservationAdmin(PopulateCreatedAndModifiedMixin, CommonExcludeMixin, admin.ModelAdmin):
    pass


class ResourceTypeAdmin(PopulateCreatedAndModifiedMixin, CommonExcludeMixin, TranslationAdmin):
    pass


class EquipmentCategoryAdmin(PopulateCreatedAndModifiedMixin, TranslationAdmin):
    pass


class PurposeAdmin(PopulateCreatedAndModifiedMixin, CommonExcludeMixin, TranslationAdmin):
    pass


admin_site.register(ResourceImage, ResourceImageAdmin)
admin_site.register(Resource, ResourceAdmin)
admin_site.register(Reservation, ReservationAdmin)
admin_site.register(ResourceType, ResourceTypeAdmin)
admin_site.register(Purpose, PurposeAdmin)
admin_site.register(Day)
admin_site.register(Unit, UnitAdmin)
admin_site.register(Equipment, EquipmentAdmin)
admin_site.register(ResourceEquipment, ResourceEquipmentAdmin)
admin_site.register(EquipmentCategory, EquipmentCategoryAdmin)
