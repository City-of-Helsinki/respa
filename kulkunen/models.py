import logging
import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ImproperlyConfigured
from django.db import models, transaction
from django.utils import timezone
from django.utils.module_loading import import_string
from django.utils.translation import ugettext_lazy as _

from resources.models import Resource

User = get_user_model()

logger = logging.getLogger(__name__)

DRIVERS = (
    ('sipass', 'Siemens SiPass', 'kulkunen.drivers.sipass.SiPassDriver'),
)

driver_classes = {}


class AccessControlUserQuerySet(models.QuerySet):
    def active(self):
        m = self.model
        return self.filter(state=m.INSTALLED)


class AccessControlUser(models.Model):
    INSTALLED = 'installed'
    REMOVED = 'removed'
    STATE_CHOICES = (
        (INSTALLED, _('installed')),
        (REMOVED, _('removed')),
    )

    system = models.ForeignKey('AccessControlSystem', related_name='users', on_delete=models.CASCADE)
    user = models.ForeignKey(
        User, related_name='access_control_users', on_delete=models.SET_NULL, null=True, blank=True
    )
    state = models.CharField(
        max_length=20, choices=STATE_CHOICES, default=INSTALLED, editable=False,
        help_text=_('State of the user')
    )

    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    removed_at = models.DateTimeField(null=True, blank=True)
    identifier = models.CharField(
        max_length=100, null=True, blank=True, verbose_name=_('identifier'),
        help_text=_('Identifier of user in the access control system (if any)')
    )

    driver_data = JSONField(null=True, blank=True)

    objects = AccessControlUserQuerySet.as_manager()

    class Meta:
        index_together = (('system', 'state'),)

    def __str__(self) -> str:
        name = ' '.join([x for x in (self.first_name, self.last_name) if x])
        user_uuid = str(self.user.uuid) if self.user.uuid else _("[No identifier]")
        if name:
            return _("{uuid}: {name}").format(uuid=user_uuid, name=name)
        else:
            return _("{uuid}").format(uuid=user_uuid)


class AccessControlGrantQuerySet(models.QuerySet):
    def active(self):
        m = self.model
        return self.filter(state__in=(m.REQUESTED, m.INSTALLING, m.INSTALLED, m.REMOVING))


class AccessControlGrant(models.Model):
    REQUESTED = 'requested'
    INSTALLING = 'installing'
    INSTALLED = 'installed'
    CANCELLED = 'cancelled'
    REMOVING = 'removing'
    REMOVED = 'removed'
    STATE_CHOICES = (
        (REQUESTED, _('requested')),
        (INSTALLED, _('installed')),
        (CANCELLED, _('cancelled')),
        (REMOVING, _('removing')),
        (REMOVED, _('removed')),
    )

    user = models.ForeignKey(
        AccessControlUser, related_name='grants', null=True, blank=True, on_delete=models.SET_NULL
    )
    resource = models.ForeignKey('AccessControlResource', related_name='grants', on_delete=models.CASCADE)

    # If a Respa reservation is deleted, it will be marked as None here.
    # AccessControlReservation with reservation == None should be deleted.
    reservation = models.ForeignKey(
        'resources.Reservation', on_delete=models.SET_NULL, null=True, related_name='access_control_grants'
    )
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)

    # These are set if the grants are to be installed and removed at a later time.
    install_at = models.DateTimeField(null=True, blank=True)
    remove_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    removed_at = models.DateTimeField(auto_now_add=True)

    access_code = models.CharField(verbose_name=_('access code'), max_length=32, null=True, blank=True)
    state = models.CharField(
        max_length=20, choices=STATE_CHOICES, default=REQUESTED, editable=False,
        help_text=_('State of the grant')
    )
    identifier = models.CharField(
        max_length=100, null=True, blank=True, verbose_name=_('identifier'),
        help_text=_('Identifier of grant in the access control system (if any)')
    )
    installation_failures = models.PositiveIntegerField(
        default=0, editable=False, help_text=_('How many times the system has tried to install this grant and failed')
    )
    removal_failures = models.PositiveIntegerField(
        default=0, editable=False, help_text=_('How many times the system has tried to remove this grant (and failed)')
    )

    driver_data = JSONField(null=True, blank=True)

    objects = AccessControlGrantQuerySet.as_manager()

    class Meta:
        index_together = (('resource', 'state'),)

    def __str__(self) -> str:
        return _("{user} {reservation} ({state})").format(
            user=self.user, reservation=self.reservation, state=self.state
        )

    def cancel(self):
        """Cancels a grant.

        The method checks if the grant was installed into the access control system
        already and asks for its revocation is it was. Otherwise the grant is just marked
        as removed.
        """
        logger.info('[%s] Canceling' % self)
        if self.state not in (self.REQUESTED, self.INSTALLED):
            logger.warn('[%s] Cancel called in invalid state')
            return

        if self.state == self.REQUESTED:
            self.state = self.REMOVED
        else:
            self.state = self.CANCELLED
        self.save(update_fields=['state'])
        if self.state == self.CANCELLED:
            self.resource.system.prepare_remove_grant(self)

    def install(self):
        """Installs the grant to the remote access control system.
        """
        logger.info('[%s] Installing' % self)
        assert self.state == self.REQUESTED
        # Sanity check to make sure we don't try to install grants
        # for past reservations.
        if self.ends_at < timezone.now():
            logger.error('[%s] Attempted to install grant for a past reservation')
            self.cancel()
            return

        with transaction.atomic():
            # Set the state while locking the resource to protect against race
            # conditions.
            db_self = AccessControlGrant.objects.select_related('resource').select_for_update().get(id=self.id)
            if db_self.state != self.REQUESTED:
                logger.error('[%s] Race condition with grant' % self)
                return

            self.state = self.INSTALLING
            # After the state is set to 'installing', we have exclusive access.
            self.save(update_fields=['state'])

        try:
            self.resource.system.install_grant(self)
        except Exception as e:
            logger.exception('[%s] Failed to grant access' % self)

            # If we fail, we retry after a while
            self.installation_failures += 1
            self.state = self.REQUESTED
            min_delay = min(1 << self.installation_failures, 30 * 60)
            retry_delay = random.randint(min_delay, 2 * min_delay)
            self.install_at = timezone.now() + timedelta(seconds=retry_delay)
            self.save(update_fields=['state', 'installation_failures', 'install_at'])
            logger.info('[%s] Retrying after %d seconds' % (self, retry_delay))

    def remove(self):
        """Removes the grant from the remote access control system.
        """
        logger.info('[%s] Removing' % self)
        assert self.state in (self.INSTALLED, self.CANCELLED)
        old_state = self.state
        with transaction.atomic():
            db_self = AccessControlGrant.objects.select_related('resource').select_for_update().get(id=self.id)
            if db_self.state != old_state:
                logger.error('[%s] Race condition with grant' % self)
                return

            self.state = self.REMOVING
            self.save(update_fields=['state'])

        try:
            self.resource.system.remove_grant(self)
        except Exception as e:
            logger.exception('[%s] Failed to revoke access' % self)

            # If we fail, we retry after a while
            self.removal_failures += 1
            self.state = old_state
            min_delay = min(1 << self.removal_failures, 30 * 60)
            retry_delay = random.randint(min_delay, 2 * min_delay)
            self.remove_at = timezone.now() + timedelta(seconds=retry_delay)
            self.save(update_fields=['state', 'removal_failures', 'remove_at'])
            logger.info('[%s] Retrying after %d seconds' % (self, retry_delay))

    def notify_access_code(self):
        reservation = self.reservation
        reservation.access_code = self.access_code
        reservation.save(update_fields=['access_code'])
        logger.info('Notifying access code creation')
        reservation.send_access_code_created_mail()


class AccessControlResource(models.Model):
    system = models.ForeignKey(
        'AccessControlSystem', related_name='resources', on_delete=models.CASCADE,
        verbose_name=_('system')
    )
    # If a Respa resource is deleted, it will be marked as None here.
    # AccessControlResources with resource == None should be deleted.
    resource = models.ForeignKey(
        'resources.Resource', related_name='access_control_resources', on_delete=models.SET_NULL,
        verbose_name=_('resource'), null=True
    )
    identifier = models.CharField(
        max_length=100, null=True, blank=True, verbose_name=_('identifier'),
        help_text=_('Identifier of resource in the access control system (if any)')
    )

    driver_config = JSONField(null=True, blank=True, help_text=_('Driver-specific configuration'))
    driver_data = JSONField(null=True, editable=False, help_text=_('Internal driver data'))

    class Meta:
        unique_together = (('system', 'resource'),)

    def __str__(self) -> str:
        return "%s: %s" % (self.system, self.resource)

    def save(self, *args, **kwargs):
        self.system.save_resource(self)
        super().save(*args, **kwargs)

    def pad_start_and_end_times(self, start, end):
        system = self.system
        leeway = system.reservation_leeway or 0
        start -= timedelta(minutes=leeway)
        end += timedelta(minutes=leeway)
        return start, end

    def _grant_has_changed(self, old_grant, new_grant):
        if old_grant.user:
            user = old_grant.user.user
            if new_grant.reservation.user != user:
                return True

        if old_grant.starts_at != new_grant.starts_at:
            return True
        if old_grant.ends_at != new_grant.ends_at:
            return True
        return False

    def grant_access(self, reservation):
        assert reservation.resource == self.resource
        grant = AccessControlGrant(
            resource=self, reservation=reservation, state=AccessControlGrant.REQUESTED
        )
        grant.starts_at, grant.ends_at = self.pad_start_and_end_times(reservation.begin, reservation.end)

        with transaction.atomic():
            existing_grants = reservation.access_control_grants\
                .filter(resource=self).active().select_related('resource').select_for_update()
            old_grant = None
            assert len(existing_grants) <= 1
            if existing_grants:
                old_grant = existing_grants[0]
                if not self._grant_has_changed(old_grant, grant):
                    return old_grant
                else:
                    old_grant.cancel()
            grant.save()

        self.system.prepare_install_grant(grant)
        return grant

    def revoke_access(self, reservation):
        assert reservation.resource == self.resource
        with transaction.atomic():
            existing_grants = reservation.access_control_grants\
                .filter(resource=self).active().select_related('resource').select_for_update()
            assert len(existing_grants) <= 1
            if not existing_grants:
                return
            grant = existing_grants[0]
            grant.cancel()

    def driver_identifier(self):
        return self.system.get_resource_identifier(self)

    def active_grant_count(self):
        return self.grants.active().count()


class AccessControlSystem(models.Model):
    name = models.CharField(max_length=100, unique=True)
    driver = models.CharField(max_length=30, choices=[(x[0], x[1]) for x in DRIVERS])

    reservation_leeway = models.PositiveIntegerField(
        null=True, blank=True, verbose_name=_('reservation leeway'),
        help_text=_('How many minutes before and after the reservation the access will be allowed')
    )

    driver_config = JSONField(null=True, blank=True, help_text=_('Driver-specific configuration'))
    driver_data = JSONField(null=True, editable=False, help_text=_('Internal driver data'))

    # Cached driver instance
    _driver = None

    def clean(self):
        driver = self._get_driver()
        driver.validate_system_config(self.driver_config)

    def __str__(self) -> str:
        return "{name} ({driver})".format(name=self.name, driver=self.driver)

    def _get_driver(self):
        if self._driver is not None:
            return self._driver

        driver_class = driver_classes.get(self.driver)
        if driver_class is None:
            for name, verbose_name, driver_path in DRIVERS:
                if name == self.driver:
                    break
            else:
                raise ImproperlyConfigured("Driver %s not found" % self.driver)

            driver_class = import_string(driver_path)
            driver_classes[self.driver] = driver_class

        self._driver = driver_class(self)
        return self._driver

    def prepare_install_grant(self, grant: AccessControlGrant):
        self._get_driver().prepare_install_grant(grant)

    def prepare_remove_grant(self, grant: AccessControlGrant):
        self._get_driver().prepare_remove_grant(grant)

    def install_grant(self, grant: AccessControlGrant):
        self._get_driver().install_grant(grant)

    def remove_grant(self, grant: AccessControlGrant):
        self._get_driver().remove_grant(grant)

    def get_system_config_schema(self):
        return self._get_driver().get_system_config_schema()

    def get_resource_config_schema(self):
        return self._get_driver().get_resource_config_schema()

    def get_resource_identifier(self, resource: AccessControlResource):
        return self._get_driver().get_resource_identifier(resource)

    def save_respa_resource(self, resource: AccessControlResource, respa_resource: Resource):
        """Notify driver about saving a Respa resource

        Allows for driver-specific customization of the Respa resource or the
        corresponding access control resource. Called when the Respa resource object is saved.
        NOTE: The driver must not call `respa_resource.save()`. Saving the resource
        is handled automatically later.
        """
        self._get_driver().save_respa_resource(resource, respa_resource)

    def save_resource(self, resource: AccessControlResource):
        """Notify driver about saving an access control resource

        Allows for driver-specific customization of the access control resource or the
        corresponding Respa resource. Called when the access control resource is saved.
        """
        self._get_driver().save_resource(resource)
