from modeltranslation.translator import TranslationOptions, register

from .models import CateringProduct, CateringProductCategory, CateringProvider


@register(CateringProduct)
class CateringProductTranslationOptions(TranslationOptions):
    fields = ('name', 'description')


@register(CateringProductCategory)
class CateringProductCategoryTranslationOptions(TranslationOptions):
    fields = ('name',)


@register(CateringProvider)
class CateringProviderTranslationOptions(TranslationOptions):
    fields = ('price_list_url',)
