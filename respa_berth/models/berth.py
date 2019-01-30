from django.contrib.gis.db import models
from django.utils.translation import ugettext_lazy as _
from resources.models import Resource
from users.models import User

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
    reserving = models.DateTimeField(verbose_name=_('Reserving'), blank=True, null=True)
    reserving_staff_member = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return "%s" % self.resource.name

    def get_name_and_unit(self):
        return "%s / %s" % (self.resource.name, self.resource.unit.name)

class GroundBerthPrice(models.Model):
    price = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    created = models.DateTimeField(_(u'created'), auto_now_add=True)

    def __str__(self):
        return "%s" % str(self.price)
