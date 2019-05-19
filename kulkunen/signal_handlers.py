import logging

from django.apps import apps
from django.db.models.signals import pre_save

from resources.signals import reservation_cancelled, reservation_confirmed, reservation_modified

logger = logging.getLogger(__name__)


def _get_acr(resource):
    acr = list(resource.access_control_resources.all())
    if not len(acr):
        return None
    if len(acr) > 1:
        logger.error('Currently supporting only one access control resource per Respa resource')
    return acr[0]


def handle_reservation_confirmed(sender, **kwargs):
    reservation = kwargs.get('instance')
    acr = _get_acr(reservation.resource)
    if not acr:
        return
    acr.grant_access(reservation)


def handle_reservation_cancelled(sender, **kwargs):
    reservation = kwargs.get('instance')
    acr = _get_acr(reservation.resource)
    if not acr:
        return
    acr.revoke_access(reservation)


def handle_reservation_modified(sender, **kwargs):
    reservation = kwargs.get('instance')
    acr = _get_acr(reservation.resource)
    if not acr:
        return
    acr.grant_access(reservation)


def handle_respa_resource_save(sender, **kwargs):
    resource = kwargs.get('instance')
    acr = _get_acr(resource)
    if not acr:
        return
    acr.system.save_respa_resource(acr, resource)


def install_signal_handlers():
    reservation_confirmed.connect(handle_reservation_confirmed)
    reservation_cancelled.connect(handle_reservation_cancelled)
    reservation_modified.connect(handle_reservation_modified)

    Resource = apps.get_model(app_label='resources', model_name='Resource')
    pre_save.connect(handle_respa_resource_save, sender=Resource)
