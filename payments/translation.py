from modeltranslation.translator import TranslationOptions, register

from .models import Product


@register(Product)
class ProductTranslationOptions(TranslationOptions):
    fields = ('name', 'description')
