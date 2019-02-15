import logging
from contextlib import contextmanager

from django.core.exceptions import ImproperlyConfigured  # noqa
from django.db import transaction
from django.utils import timezone

from resources.models import Resource

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
        with self.system_lock() as system:
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
            yield AccessControlSystem.objects.select_for_update().get(id=self.system.id)

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

    def get_system_config_schema(self):
        raise NotImplementedError("Implement this in the driver")

    def get_resource_config_schema(self):
        raise NotImplementedError("Implement this in the driver")

    def get_resource_identifier(self, resource: AccessControlResource):
        """Get a driver-specific, human-readable resource identifier to display in UI

        Should be overridden by the driver implementation if needed.
        """
        return ''

    def save_respa_resource(self, resource: AccessControlResource, respa_resource: Resource):
        """Notify driver about saving a Respa resource

        Allows for driver-specific customization of the Respa resource or the
        corresponding access control resource. Called when the Respa resource object is saved.
        NOTE: The driver must not call `respa_resource.save()`. Saving the resource
        is handled automatically later.
        """
        pass

    def save_resource(self, resource: AccessControlResource):
        """Notify driver about saving an access control resource

        Allows for driver-specific customization of the access control resource or the
        corresponding Respa resource. Called when the access control resource is saved.

        Should be overridden by the driver implementation if needed
        """
        pass
