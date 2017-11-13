"""
Upload Respa reservations into Exchange as calendar events.
"""
import logging

from django.utils.encoding import force_text

from resources.models import Reservation
from respa_exchange.ews.calendar import CreateCalendarItemRequest, DeleteCalendarItemRequest, UpdateCalendarItemRequest

log = logging.getLogger(__name__)


def _build_subject(res):
    """
    Build a subject line for the given Reservation, to be sent to Exchange

    :type res: resources.models.Reservation
    :return: str
    """
    if res.event_subject:
        return res.event_subject

    bits = ["Respa"]
    if res.reserver_name:
        bits.append(res.reserver_name)
    elif res.user_id:
        bits.append(res.user)
    return " - ".join(force_text(bit) for bit in bits)


def _build_body(res):
    """
    Build the body of the Exchange appointment for a given Reservation.

    :type res: resources.models.Reservation
    :return: str
    """
    return res.event_description or ''


def _build_location(exres, res):
    resource = res.resource
    if resource.name:
        if resource.unit:
            return "%s (%s)" % (resource.name, resource.unit.name)
        return resource.name
    return exres.principal_email


def _get_calendar_item_props(exres):
    res = exres.reservation
    assert isinstance(res, Reservation)
    ret = dict(
        start=res.begin,
        end=res.end,
        subject=_build_subject(res),
        body=_build_body(res),
        location=_build_location(exres, res)
    )
    if res.user and res.user.email:
        ret['required_attendees'] = [res.user.email]
    return ret


def create_on_remote(exres):
    """
    Create and link up an appointment for an ExchangeReservation.

    :param exres: Exchange Reservation
    :type exres: respa_exchange.models.ExchangeReservation
    """
    res = exres.reservation
    if res.state != Reservation.CONFIRMED:
        return
    assert isinstance(res, Reservation)

    send_notifications = True
    if getattr(res, '_skip_notifications', False):
        send_notifications = False

    ccir = CreateCalendarItemRequest(
        principal=force_text(exres.principal_email),
        item_props=_get_calendar_item_props(exres),
        send_notifications=send_notifications
    )
    exres.item_id = ccir.send(exres.exchange.get_ews_session())
    exres.save()
    log.info("Created calendar item for %s", exres)


def update_on_remote(exres):
    """
    Update (or delete) the Exchange appointment for an ExchangeReservation.

    :param exres: Exchange Reservation
    :type exres: respa_exchange.models.ExchangeReservation
    """
    res = exres.reservation
    if res.state in (Reservation.DENIED, Reservation.CANCELLED):
        return delete_on_remote(exres)

    send_notifications = True
    if getattr(res, '_skip_notifications', False):
        send_notifications = False

    # TODO: Should we try and track the state of the object to avoid sending superfluous updates?
    ucir = UpdateCalendarItemRequest(
        principal=force_text(exres.principal_email),
        item_id=exres.item_id,
        update_props=_get_calendar_item_props(exres),
        send_notifications=send_notifications
    )
    exres.item_id = ucir.send(exres.exchange.get_ews_session())
    exres.save()

    log.info("Updated calendar item for %s", exres)


def delete_on_remote(exres):
    """
    Delete the Exchange appointment for an ExchangeReservation.

    :param exres: Exchange Reservation
    :type exres: respa_exchange.models.ExchangeReservation
    """
    send_notifications = True
    if getattr(exres.reservation, '_skip_notifications', False):
        send_notifications = False
    dcir = DeleteCalendarItemRequest(
        principal=exres.principal_email,
        item_id=exres.item_id,
        send_notifications=send_notifications
    )
    dcir.send(exres.exchange.get_ews_session())
    log.info("Deleted %s", exres)
    exres.delete()
