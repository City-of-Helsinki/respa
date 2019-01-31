import logging

from resources.signals import reservation_cancelled, reservation_confirmed, reservation_modified

logger = logging.getLogger(__name__)


def _get_acr(reservation):
    acr = list(reservation.resource.access_control_resources.all())
    if not len(acr):
        return None
    if len(acr) > 1:
        logger.error('Currently supporting only one access control resource per Respa resource')
    return acr[0]


def handle_reservation_confirmed(sender, **kwargs):
    reservation = kwargs.get('instance')
    acr = _get_acr(reservation)
    if not acr:
        return
    acr.grant_access(reservation)


def handle_reservation_cancelled(sender, **kwargs):
    reservation = kwargs.get('instance')
    acr = _get_acr(reservation)
    if not acr:
        return
    acr.revoke_access(reservation)


def handle_reservation_modified(sender, **kwargs):
    reservation = kwargs.get('instance')
    acr = _get_acr(reservation)
    if not acr:
        return
    acr.grant_access(reservation)


def install_signal_handlers():
    reservation_confirmed.connect(handle_reservation_confirmed)
    reservation_cancelled.connect(handle_reservation_cancelled)
    reservation_modified.connect(handle_reservation_modified)
