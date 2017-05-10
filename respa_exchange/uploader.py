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
    bits = []
    for field in Reservation._meta.get_fields():
        try:
            val = getattr(res, field.attname)
        except AttributeError:
            continue
        if not val:
            continue
        bits.append("%s: %s" % (field.verbose_name, val))
    return "\n".join(bits)


def _get_calendar_item_props(exres):
    res = exres.reservation
    assert isinstance(res, Reservation)
    return dict(
        start=res.begin,
        end=res.end,
        subject=_build_subject(res),
        body=_build_body(res),
        location=force_text(res.resource)
    )


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

    ccir = CreateCalendarItemRequest(
        principal=force_text(exres.principal_email),
        item_props=_get_calendar_item_props(exres),
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
    # TODO: Should we try and track the state of the object to avoid sending superfluous updates?
    ucir = UpdateCalendarItemRequest(
        principal=force_text(exres.principal_email),
        item_id=exres.item_id,
        update_props=_get_calendar_item_props(exres),
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
    dcir = DeleteCalendarItemRequest(
        principal=exres.principal_email,
        item_id=exres.item_id
    )
    dcir.send(exres.exchange.get_ews_session())
    log.info("Deleted %s", exres)
    exres.delete()
