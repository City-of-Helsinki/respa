from modeltranslation.translator import TranslationOptions, register

from .models import Unit, Resource, ResourceType, ResourceImage, Purpose
from .models import Equipment, ResourceEquipment, EquipmentCategory


@register(Unit)
class UnitTranslationOptions(TranslationOptions):
    fields = ('name', 'www_url', 'street_address', 'description',
              'picture_caption')


@register(Resource)
class ResourceTranslationOptions(TranslationOptions):
    fields = ('name', 'description')


@register(ResourceType)
class ResourceTypeTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(ResourceImage)
class ResourceImageTranslationOptions(TranslationOptions):
    fields = ('caption',)


@register(Purpose)
class PurposeTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(Equipment)
class EquipmentTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(ResourceEquipment)
class ResourceEquipmentTranslationOptions(TranslationOptions):
    fields = ('description',)


@register(EquipmentCategory)
class EquipmentCategoryTranslationOptions(TranslationOptions):
    fields = ('name',)
