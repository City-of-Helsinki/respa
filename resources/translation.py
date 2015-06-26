from modeltranslation.translator import translator, TranslationOptions
from .models import Unit


class UnitTranslationOptions(TranslationOptions):
    fields = ('name', 'www_url', 'street_address', 'description',
              'picture_caption')

translator.register(Unit, UnitTranslationOptions)
