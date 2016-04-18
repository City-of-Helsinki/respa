"""
Download Exchange events into Respa as reservations.
"""
import datetime

import iso8601
from django.db.transaction import atomic
from django.utils.timezone import now

from resources.models.reservation import Reservation
from respa_exchange.ews.calendar import GetCalendarItemsRequest
from respa_exchange.ews.objs import ItemID
from respa_exchange.ews.xml import NAMESPACES
from respa_exchange.models import ExchangeReservation


def _populate_reservation(reservation, ex_resource, item_props):
    """
    Populate a Reservation instance based on Exchange data

    :type reservation: resources.models.Reservation
    :type ex_resource: respa_exchange.models.ExchangeResource
    :type item_props: dict
    :return:
    """
    comment_text = "%s\nSynchronized from Exchange %s" % (item_props["subject"], ex_resource.exchange)
    reservation.begin = item_props["start"]
    reservation.end = item_props["end"]
    reservation.comments = comment_text
    reservation._from_exchange = True  # Set a flag to prevent immediate re-upload
    return reservation


def _update_reservation_from_exchange(item_id, ex_reservation, ex_resource, item_props):
    reservation = ex_reservation.reservation
    _populate_reservation(reservation, ex_resource, item_props)
    reservation.save()
    ex_reservation.item_id = item_id
    ex_reservation.save()


def _create_reservation_from_exchange(item_id, ex_resource, item_props):
    reservation = Reservation(resource=ex_resource.resource)
    _populate_reservation(reservation, ex_resource, item_props)
    reservation.save()
    ex_reservation = ExchangeReservation(
        exchange=ex_resource.exchange,
        principal_email=ex_resource.principal_email,
        reservation=reservation,
        managed_in_exchange=True,
    )
    ex_reservation.item_id = item_id
    ex_reservation.save()
    return ex_reservation


@atomic
def sync_from_exchange(ex_resource, future_days=30):
    """
    Synchronize from Exchange to Respa

    Synchronizes current and future events for the given Exchange resource into
    the relevant Respa resource as reservations.

    :param ex_resource: The Exchange resource to sync
    :type ex_resource: respa_exchange.models.ExchangeResource
    :param future_days: How many days into the future to look
    :type future_days: int
    """
    if not ex_resource.sync_to_respa:
        return
    start_date = now()
    end_date = start_date + datetime.timedelta(days=future_days)
    gcir = GetCalendarItemsRequest(
        principal=ex_resource.principal_email,
        start_date=start_date,
        end_date=end_date
    )
    session = ex_resource.exchange.get_ews_session()
    calendar_items = {}
    for item in gcir.send(session):
        calendar_items[ItemID.from_tree(item)] = item

    hashes = set(item_id.hash for item_id in calendar_items.keys())

    # First handle deletions . . .

    items_to_delete = ExchangeReservation.objects.select_related("reservation").filter(
        managed_in_exchange=True,  # Reservations we've downloaded ...
        reservation__begin__gte=start_date.date(),  # that are in ...
        reservation__end__lte=end_date.date(),  # ... our get items range ...
    ).exclude(item_id_hash__in=hashes)  # but aren't ones we're going to mangle

    for ex_reservation in items_to_delete:
        reservation = ex_reservation.reservation
        ex_reservation.delete()
        reservation.delete()

    # And then creations/additions

    extant_exchange_reservations = {
        ex_reservation.item_id_hash: ex_reservation
        for ex_reservation
        in ExchangeReservation.objects.select_related("reservation").filter(item_id_hash__in=hashes)
    }

    for item_id, item in calendar_items.items():
        ex_reservation = extant_exchange_reservations.get(item_id.hash)
        item_props = dict(
            start=iso8601.parse_date(item.find("t:Start", namespaces=NAMESPACES).text),
            end=iso8601.parse_date(item.find("t:End", namespaces=NAMESPACES).text),
            subject=item.find("t:Subject", namespaces=NAMESPACES).text,
        )

        if not ex_reservation:  # It's a new one!
            ex_reservation = _create_reservation_from_exchange(item_id, ex_resource, item_props)
        else:
            res = ex_reservation.reservation
            if res.begin != item_props["start"] or res.end != item_props["end"]:
                # Important things changed, so edit the reservation
                _update_reservation_from_exchange(item_id, ex_reservation, ex_resource, item_props)
