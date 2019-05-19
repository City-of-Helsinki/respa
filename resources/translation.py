from modeltranslation.translator import TranslationOptions, register

from .models import (
    Equipment, EquipmentCategory, Purpose, Resource, ResourceEquipment,
    ResourceImage, ResourceType, TermsOfUse, Unit, UnitGroup)


@register(UnitGroup)
class UnitGroupTranslationOptions(TranslationOptions):
    fields = ['name']


@register(Unit)
class UnitTranslationOptions(TranslationOptions):
    fields = ('name', 'www_url', 'street_address', 'description',
              'picture_caption')


@register(Resource)
class ResourceTranslationOptions(TranslationOptions):
    fields = ('name', 'description', 'specific_terms',
              'reservation_confirmed_notification_extra',
              'reservation_requested_notification_extra',
              'reservation_info', 'responsible_contact_info')


@register(ResourceType)
class ResourceTypeTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(ResourceImage)
class ResourceImageTranslationOptions(TranslationOptions):
    fields = ('caption',)


@register(Purpose)
class PurposeTranslationOptions(TranslationOptions):
    fields = ('name',)
    required_languages = ('fi', 'en')


@register(Equipment)
class EquipmentTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(ResourceEquipment)
class ResourceEquipmentTranslationOptions(TranslationOptions):
    fields = ('description',)


@register(EquipmentCategory)
class EquipmentCategoryTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(TermsOfUse)
class TermsOfUserTranslationOptions(TranslationOptions):
    fields = ('name', 'text')
