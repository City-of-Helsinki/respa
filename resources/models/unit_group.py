from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
from enumfields import EnumField

from ..auth import is_authenticated_user, is_general_admin
from ..enums import UnitGroupAuthorizationLevel
from .base import ModifiableModel
from .unit import Unit


class UnitGroup(ModifiableModel):
    name = models.CharField(max_length=200)
    members = models.ManyToManyField(Unit, related_name='unit_groups')

    class Meta:
        verbose_name = _("unit group")
        verbose_name_plural = _("unit groups")

    def __str__(self):
        return self.name

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
    subject = models.ForeignKey(
        UnitGroup, on_delete=models.CASCADE, related_name='authorizations',
        verbose_name=_("subject of the authorization"))
    level = EnumField(
        UnitGroupAuthorizationLevel, max_length=50,
        verbose_name=_("authorization level"))
    authorized = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='unit_group_authorizations',
        verbose_name=_("authorized user"))

    class Meta:
        unique_together = [('authorized', 'subject', 'level')]
        verbose_name = _("unit group authorization")
        verbose_name_plural = _("unit group authorizations")

    objects = UnitGroupAuthorizationQuerySet.as_manager()

    def __str__(self):
        return '{unit_group} / {level}: {user}'.format(
            unit_group=self.subject, level=self.level, user=self.authorized)
