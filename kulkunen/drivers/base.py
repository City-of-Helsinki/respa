import logging
from contextlib import contextmanager

from django.core.exceptions import ImproperlyConfigured  # noqa
from django.db import transaction
from django.utils import timezone

from ..models import AccessControlGrant, AccessControlResource, AccessControlSystem


class RemoteError(Exception):
    pass


class AccessControlDriver:
    def __init__(self, system: AccessControlSystem):
        self.system = system
        self.logger = logging.getLogger(str(self.__class__))

    def get_setting(self, name: str, missing_none=False):
        if name not in self.system.driver_config and hasattr(self, 'DEFAULT_CONFIG'):
            if missing_none and name not in self.DEFAULT_CONFIG:
                return None
            return self.DEFAULT_CONFIG[name]
        if missing_none and name not in self.system.driver_config:
            return None
        return self.system.driver_config[name]

    def update_driver_data(self, settings: dict):
        with transaction.atomic():
            system = AccessControlSystem.objects.select_for_update().get(id=self.system.id)
            if system.driver_data is None:
                system.driver_data = {}
            system.driver_data.update(settings)
            system.save(update_fields=['driver_data'])

    def get_driver_data(self) -> dict:
        system = AccessControlSystem.objects.get(id=self.system.id)
        if system.driver_data is None:
            return {}
        return system.driver_data

    @contextmanager
    def system_lock(self):
        with transaction.atomic():
            AccessControlSystem.objects.select_for_update().get(id=self.system.id)
            yield

    def install_grant(self, grant: AccessControlGrant):
        raise NotImplementedError("Implement this in the driver")

    def remove_grant(self, grant: AccessControlGrant):
        raise NotImplementedError("Implement this in the driver")

    def prepare_install_grant(self, grant: AccessControlGrant):
        grant.install_at = timezone.now()
        grant.save(update_fields=['install_at'])

    def prepare_remove_grant(self, grant: AccessControlGrant):
        grant.remove_at = timezone.now()
        grant.save(update_fields=['remove_at'])

    def validate_system_config(self, config: dict):
        raise NotImplementedError("Implement this in the driver")

    def validate_resource_config(self, resource: AccessControlResource):
        raise NotImplementedError("Implement this in the driver")
