from django.contrib.gis.db import models
from django.utils.translation import ugettext_lazy as _
from resources.models import Resource

class Berth(models.Model):
    DOCK = 'dock'
    GROUND = 'ground'
    NUMBER = 'number'

    TYPE_CHOICES = (
        (DOCK, _('dock')),
        (GROUND, _('ground')),
        (NUMBER, _('number')),
    )

    resource = models.OneToOneField(Resource, verbose_name=_('Resource'), db_index=True, on_delete=models.CASCADE)
    width_cm = models.PositiveSmallIntegerField(verbose_name=_('Berth width'), null=True, blank=True)
    depth_cm = models.PositiveSmallIntegerField(verbose_name=_('Berth depth'), null=True, blank=True)
    length_cm = models.PositiveSmallIntegerField(verbose_name=_('Berth length'), null=True, blank=True)
    price = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    type = models.CharField(choices=TYPE_CHOICES, verbose_name=_('Berth type'), default=DOCK, max_length=20)
    is_disabled = models.BooleanField(default=False)

    def __str__(self):
        return "%s" % self.resource.name