from django.conf import settings
from django.db import models
from enumfields import EnumField

from ..enums import UnitGroupAuthorizationLevel
from .base import ModifiableModel
from .unit import Unit


class UnitGroup(ModifiableModel):
    name = models.CharField(max_length=200)
    members = models.ManyToManyField(Unit, related_name='unit_groups')


class UnitGroupAuthorization(models.Model):
    authorized = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='unit_group_authorizations')
    subject = models.ForeignKey(
        UnitGroup, on_delete=models.CASCADE, related_name='authorizations')
    level = EnumField(UnitGroupAuthorizationLevel, max_length=50)

    class Meta:
        unique_together = [('authorized', 'subject', 'level')]
