from django.contrib.gis.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import pgettext_lazy
from django.conf import settings

from .base import AutoIdentifiedModel, ModifiableModel
from .utils import get_translated, DEFAULT_LANG


class EquipmentCategory(ModifiableModel, AutoIdentifiedModel):
    id = models.CharField(primary_key=True, max_length=100)
    name = models.CharField(verbose_name=_('Name'), max_length=200)

    class Meta:
        verbose_name = _('equipment category')
        verbose_name_plural = _('equipment categories')

    def __str__(self):
        return "%s (%s)" % (get_translated(self, 'name'), self.id)


class Equipment(ModifiableModel, AutoIdentifiedModel):
    id = models.CharField(primary_key=True, max_length=100)
    name = models.CharField(verbose_name=_('Name'), max_length=200)
    category = models.ForeignKey(EquipmentCategory, verbose_name=_('Category'), related_name='equipment',
                                 on_delete=models.CASCADE)

    class Meta:
        verbose_name = pgettext_lazy('singular', 'equipment')
        verbose_name_plural = pgettext_lazy('plural', 'equipment')
        ordering = ('category', 'name')

    def __str__(self):
        return get_translated(self, 'name')


class EquipmentAlias(ModifiableModel, AutoIdentifiedModel):
    id = models.CharField(primary_key=True, max_length=100)
    name = models.CharField(verbose_name=_('Name'), max_length=200)
    language = models.CharField(choices=settings.LANGUAGES, default=DEFAULT_LANG, max_length=3)
    equipment = models.ForeignKey(Equipment, related_name='aliases', on_delete=models.CASCADE)

    class Meta:
        verbose_name = _('equipment alias')
        verbose_name_plural = _('equipment aliases')

    def __str__(self):
        return "%s (%s)" % (get_translated(self, 'name'), self.equipment)
