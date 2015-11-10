from django.contrib.gis.db import models
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from .base import AutoIdentifiedModel, ModifiableModel
from .utils import get_translated, DEFAULT_LANG


class Equipment(ModifiableModel, AutoIdentifiedModel):
    id = models.CharField(primary_key=True, max_length=100)
    name = models.CharField(verbose_name=_('Name'), max_length=200)

    class Meta:
        verbose_name = _('equipment')
        verbose_name_plural = _('equipment')

    def __str__(self):
        return get_translated(self, 'name')


class EquipmentAlias(ModifiableModel, AutoIdentifiedModel):
    id = models.CharField(primary_key=True, max_length=100)
    name = models.CharField(verbose_name=_('Name'), max_length=200)
    language = models.CharField(choices=settings.LANGUAGES, default=DEFAULT_LANG, max_length=3)
    equipment = models.ForeignKey(Equipment, related_name='aliases')

    class Meta:
        verbose_name = _('equipment alias')
        verbose_name_plural = _('equipment aliases')

    def __str__(self):
        return "%s (%s)" % (get_translated(self, 'name'), self.equipment)
