from django.conf import settings
from django.db import models
from enumfields import EnumField

from ..auth import is_authenticated_user, is_general_admin
from ..enums import UnitGroupAuthorizationLevel
from .base import ModifiableModel
from .unit import Unit


class UnitGroup(ModifiableModel):
    name = models.CharField(max_length=200)
    members = models.ManyToManyField(Unit, related_name='unit_groups')

    def is_admin(self, user):
        return is_authenticated_user(user) and (
            user.is_superuser or
            is_general_admin(user) or
            (user.unit_group_authorizations
             .to_unit_group(self).admin_level().exists()))


class UnitGroupAuthorizationQuerySet(models.QuerySet):
    def for_user(self, user):
        return self.filter(authorized=user)

    def to_unit_group(self, unit_group):
        return self.filter(subject=unit_group)

    def to_unit(self, unit):
        return self.filter(subject__members=unit)

    def admin_level(self):
        return self.filter(level=UnitGroupAuthorizationLevel.admin)


class UnitGroupAuthorization(models.Model):
    authorized = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='unit_group_authorizations')
    subject = models.ForeignKey(
        UnitGroup, on_delete=models.CASCADE, related_name='authorizations')
    level = EnumField(UnitGroupAuthorizationLevel, max_length=50)

    class Meta:
        unique_together = [('authorized', 'subject', 'level')]

    objects = UnitGroupAuthorizationQuerySet.as_manager()
