from modeltranslation.translator import translator, TranslationOptions
from .models import *


class UnitTranslationOptions(TranslationOptions):
    fields = ('name', 'www_url', 'street_address', 'description',
              'picture_caption')


class ResourceTranslationOptions(TranslationOptions):
    fields = ('name', 'description')


class ResourceTypeTranslationOptions(TranslationOptions):
    fields = ('name',)


class PurposeTranslationOptions(TranslationOptions):
    fields = ('name',)


translator.register(Unit, UnitTranslationOptions)
translator.register(Resource, ResourceTranslationOptions)
translator.register(ResourceType, ResourceTypeTranslationOptions)
translator.register(Purpose, PurposeTranslationOptions)

