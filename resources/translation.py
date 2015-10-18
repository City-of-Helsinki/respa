from modeltranslation.translator import register, TranslationOptions
from .models import *


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

