import pytz
from django.conf import settings
from django.contrib.gis.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from enumfields import EnumField

from ..auth import is_authenticated_user, is_general_admin, is_unit_admin, is_unit_manager, is_unit_viewer, is_superuser
from ..enums import UnitAuthorizationLevel, UnitGroupAuthorizationLevel
from .base import AutoIdentifiedModel, ModifiableModel
from .utils import create_datetime_days_from_now, get_translated, get_translated_name
from .availability import get_opening_hours
from .permissions import UNIT_PERMISSIONS

from munigeo.models import Municipality


class UnitQuerySet(models.QuerySet):
    def managed_by(self, user):
        if not is_authenticated_user(user):
            return self.none()

        if is_general_admin(user):
            return self

        via_unit_group = Q(
            unit_groups__authorizations__in=(
                user.unit_group_authorizations.admin_level()))
        via_unit = Q(
            authorizations__in=(
                user.unit_authorizations.at_least_manager_level()))

        return self.filter(via_unit_group | via_unit).distinct()

    def by_roles(self, user, roles):
        if not is_authenticated_user(user) or not roles:
            return self.none()

        if is_superuser(user):
            return self

        if ((UnitAuthorizationLevel.admin in roles or UnitGroupAuthorizationLevel.admin in roles)
            and is_general_admin(user)):
            return self

        unit_roles = filter(lambda role : isinstance(role, UnitAuthorizationLevel), roles)
        unit_group_roles = filter(lambda role : isinstance(role, UnitGroupAuthorizationLevel), roles)

        via_unit_group = Q(
            unit_groups__authorizations__in=(
                user.unit_group_authorizations.filter(level__in=unit_group_roles)))

        via_unit = Q(
            authorizations__in=(
                user.unit_authorizations.filter(level__in=unit_roles)))

        return self.filter(via_unit_group | via_unit).distinct()


def _get_default_timezone():
    return timezone.get_default_timezone().zone


def _get_timezone_choices():
    return [(x, x) for x in pytz.all_timezones]


class Unit(ModifiableModel, AutoIdentifiedModel):
    id = models.CharField(primary_key=True, max_length=50)
    name = models.CharField(verbose_name=_('Name'), max_length=200)
    description = models.TextField(verbose_name=_('Description'), null=True, blank=True)

    location = models.PointField(verbose_name=_('Location'), null=True, srid=settings.DEFAULT_SRID)
    time_zone = models.CharField(verbose_name=_('Time zone'), max_length=50,
                                 default=_get_default_timezone)

    manager_email = models.EmailField(verbose_name=_('Manager email'), max_length=100, null=True, blank=True)

    street_address = models.CharField(verbose_name=_('Street address'), max_length=100, null=True)
    address_zip = models.CharField(verbose_name=_('Postal code'), max_length=10, null=True, blank=True)
    phone = models.CharField(verbose_name=_('Phone number'), max_length=30, null=True, blank=True)
    email = models.EmailField(verbose_name=_('Email'), max_length=100, null=True, blank=True)
    www_url = models.URLField(verbose_name=_('WWW link'), max_length=400, null=True, blank=True)
    address_postal_full = models.CharField(verbose_name=_('Full postal address'), max_length=100,
                                           null=True, blank=True)
    municipality = models.ForeignKey(Municipality, null=True, blank=True, verbose_name=_('Municipality'),
                                     on_delete=models.SET_NULL)

    picture_url = models.URLField(verbose_name=_('Picture URL'), max_length=200,
                                  null=True, blank=True)
    picture_caption = models.CharField(verbose_name=_('Picture caption'), max_length=200,
                                       null=True, blank=True)

    reservable_max_days_in_advance = models.PositiveSmallIntegerField(verbose_name=_('Reservable max. days in advance'),
                                                                      null=True, blank=True)
    reservable_min_days_in_advance = models.PositiveSmallIntegerField(verbose_name=_('Reservable min. days in advance'),
                                                                      null=True, blank=True)
    data_source = models.CharField(max_length=128, blank=True, default='',
                                   verbose_name=_('External data source'))
    data_source_hours = models.CharField(max_length=128, blank=True, default='',
                                         verbose_name=_('External data source for opening hours'))
    disallow_overlapping_reservations = models.BooleanField(
        verbose_name=_('Disallow overlapping reservations in this unit'),
        default=False,
    )

    objects = UnitQuerySet.as_manager()

    class Meta:
        verbose_name = _("unit")
        verbose_name_plural = _("units")
        permissions = UNIT_PERMISSIONS
        ordering = ('name',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set the time zone choices here in order to avoid spawning
        # spurious migrations.
        self._meta.get_field('time_zone').choices = _get_timezone_choices()

    def __str__(self):
        return "%s (%s)" % (get_translated(self, 'name'), self.id)

    def get_opening_hours(self, begin=None, end=None):
        """
        :rtype : dict[str, list[dict[str, datetime.datetime]]]
        :type begin: datetime.date
        :type end: datetime.date
        """
        return get_opening_hours(self.time_zone, list(self.periods.all()), begin, end)

    def update_opening_hours(self):
        for res in self.resources.all():
            res.update_opening_hours()

    def get_tz(self):
        return pytz.timezone(self.time_zone)

    def get_reservable_before(self):
        return create_datetime_days_from_now(self.reservable_max_days_in_advance)

    def get_reservable_after(self):
        return create_datetime_days_from_now(self.reservable_min_days_in_advance)

    def is_admin(self, user):
        return is_authenticated_user(user) and (
            is_general_admin(user) or
            is_unit_admin(user.unit_authorizations.all(), user.unit_group_authorizations.all(), self))

    def is_manager(self, user):
        return is_authenticated_user(user) and is_unit_manager(user.unit_authorizations.all(), self)

    def is_viewer(self, user):
        return is_authenticated_user(user) and is_unit_viewer(user.unit_authorizations.all(), self)

    def has_imported_data(self):
        return self.data_source != ''

    def has_imported_hours(self):
        return self.data_source_hours != ''

    def is_editable(self):
        """ Whether unit is editable by normal admin users or not """
        return not (self.has_imported_data() or self.has_imported_hours())


class UnitAuthorizationQuerySet(models.QuerySet):
    def for_user(self, user):
        return self.filter(authorized=user)

    def to_unit(self, unit):
        return self.filter(subject=unit)

    def admin_level(self):
        return self.filter(level=UnitAuthorizationLevel.admin)

    def manager_level(self):
        return self.filter(level=UnitAuthorizationLevel.manager)

    def at_least_manager_level(self):
        return self.filter(level__in={
            UnitAuthorizationLevel.admin,
            UnitAuthorizationLevel.manager,
        })


class UnitAuthorization(models.Model):
    subject = models.ForeignKey(
        Unit, on_delete=models.CASCADE, related_name='authorizations',
        verbose_name=_("subject of the authorization"))
    level = EnumField(
        UnitAuthorizationLevel, max_length=50,
        verbose_name=_("authorization level"))
    authorized = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='unit_authorizations',
        verbose_name=_("authorized user"))

    class Meta:
        unique_together = [('authorized', 'subject', 'level')]
        verbose_name = _("unit authorization")
        verbose_name_plural = _("unit authorizations")

    objects = UnitAuthorizationQuerySet.as_manager()

    def __str__(self):
        return '{unit} / {level}: {user}'.format(
            unit=self.subject, level=self.level, user=self.authorized)


class UnitIdentifier(models.Model):
    unit = models.ForeignKey('Unit', verbose_name=_('Unit'), db_index=True, related_name='identifiers',
                             on_delete=models.CASCADE)
    namespace = models.CharField(verbose_name=_('Namespace'), max_length=50)
    value = models.CharField(verbose_name=_('Value'), max_length=100)

    class Meta:
        verbose_name = _("unit identifier")
        verbose_name_plural = _("unit identifiers")
        unique_together = (('namespace', 'value'), ('namespace', 'unit'))

    def __str__(self):
        return '{namespace}: {value}'.format(
            namespace=self.namespace, value=self.value
        )
