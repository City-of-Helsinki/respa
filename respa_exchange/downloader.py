"""
Download Exchange events into Respa as reservations.
"""
import datetime
import logging
import iso8601

from lxml import etree
from django.db.transaction import atomic
from django.utils.timezone import now

from resources.models.reservation import Reservation
from respa_exchange.ews.calendar import GetCalendarItemsRequest, FindCalendarItemsRequest
from respa_exchange.ews.user import ResolveNamesRequest
from respa_exchange.ews.objs import ItemID
from respa_exchange.ews.xml import NAMESPACES
from respa_exchange.models import ExchangeReservation, ExchangeUser

log = logging.getLogger(__name__)


def _populate_reservation(reservation, ex_resource, item_props):
    """
    Populate a Reservation instance based on Exchange data

    :type reservation: resources.models.Reservation
    :type ex_resource: respa_exchange.models.ExchangeResource
    :type item_props: dict
    :return:
    """
    reservation.begin = item_props["start"]
    reservation.end = item_props["end"]
    reservation.event_subject = item_props["subject"]
    organizer = item_props.get("organizer")
    if organizer:
        reservation.reserver_email_address = organizer.email_address
        if organizer.given_name and organizer.surname:
            name = "%s %s" % (organizer.given_name, organizer.surname)
        else:
            name = organizer.name
        reservation.reserver_name = name or ""
        reservation.host_name = reservation.reserver_name
    comment_text = "Synchronized from Exchange %s" % ex_resource.exchange
    reservation.comments = comment_text
    reservation._from_exchange = True  # Set a flag to prevent immediate re-upload
    return reservation


def _update_reservation_from_exchange(item_id, ex_reservation, ex_resource, item_props):
    reservation = ex_reservation.reservation
    _populate_reservation(reservation, ex_resource, item_props)
    reservation.save()
    ex_reservation.item_id = item_id
    ex_reservation.organizer = item_props.get("organizer")
    ex_reservation.save()

    log.info("Updated: %s", ex_reservation)


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
    ex_reservation.organizer = item_props.get("organizer")
    ex_reservation.save()

    log.info("Created: %s", ex_reservation)
    return ex_reservation


def _determine_organizer(ex_resource, organizer):
    mailbox = organizer.find("t:Mailbox", namespaces=NAMESPACES)
    routing_type = mailbox.find("t:RoutingType", namespaces=NAMESPACES).text
    user_identifier = mailbox.find("t:EmailAddress", namespaces=NAMESPACES).text
    user_name = mailbox.find("t:Name", namespaces=NAMESPACES)
    if user_name is not None:
        user_name = user_name.text
    if routing_type == "SMTP":
        id_field = 'email_address'
        id_search_field = id_field
        user_identifier = user_identifier.lower()
    elif routing_type == "EX":
        id_field = 'x500_address'
        id_search_field = id_field + '__iexact'
    else:
        log.error("Unknown mailbox routing type (%s)" % etree.tostring(mailbox, encoding=str))
        return None

    search_args = {id_search_field: user_identifier, 'exchange': ex_resource.exchange}
    try:
        ex_user = ExchangeUser.objects.get(**search_args)
    except ExchangeUser.DoesNotExist:
        ex_user = ExchangeUser(**{id_field: user_identifier, 'exchange': ex_resource.exchange})

    # If the user name remains the same, all other info is probably okay as well.
    if ex_user.pk and user_name == ex_user.name:
        return ex_user
    ex_user.name = user_name

    req = ResolveNamesRequest([user_identifier], principal=ex_resource.principal_email)
    resolutions = req.send(ex_resource.exchange.get_ews_session())
    for res in resolutions:
        mb = res.find("t:Mailbox", namespaces=NAMESPACES)
        if mb is None:
            continue
        routing_type = mb.find("t:RoutingType", namespaces=NAMESPACES).text
        email = mb.find("t:EmailAddress", namespaces=NAMESPACES)
        contact = res.find("t:Contact", namespaces=NAMESPACES)
        if routing_type != "SMTP" or email is None or contact is None:
            log.error("Invalid response to ResolveNamesRequest (%s)" % user_identifier)
            return None

        props = dict(given_name=contact.find("t:GivenName", namespaces=NAMESPACES),
                     surname=contact.find("t:Surname", namespaces=NAMESPACES))
        # props['name'] = contact.find("t:DisplayName", namespaces=NAMESPACES),
        props = {k: v.text for k, v in props.items() if v is not None}
        email = email.text.lower()
        props['email_address'] = email
        break
    else:
        return None

    for k, v in props.items():
        setattr(ex_user, k, v)

    ex_user.save()
    return ex_user


def _parse_item_props(ex_resource, item_id, item):
    item_props = dict(
        start=iso8601.parse_date(item.find("t:Start", namespaces=NAMESPACES).text),
        end=iso8601.parse_date(item.find("t:End", namespaces=NAMESPACES).text),
        subject=item.find("t:Subject", namespaces=NAMESPACES).text,
    )
    organizer = item.find("t:Organizer", namespaces=NAMESPACES)
    if organizer is not None:
        try:
            organizer = _determine_organizer(ex_resource, organizer)
        except Exception:
            log.error("Unable to determine organizer for %s" % item_id.id, exc_info=True)
            organizer = None

    item_props["organizer"] = organizer
    # Subjects often start with the organizer name, so we strip it
    if organizer and organizer.name:
        s = organizer.name + " "
        subject = item_props["subject"]
        if subject and subject.startswith(s):
            item_props["subject"] = subject[len(s):]

    return item_props


def fetch_reservation_data(ex_reservation):
    ex_resource = ex_reservation.reservation.resource.exchange_resource
    gcir = GetCalendarItemsRequest(
        principal=ex_resource.principal_email,
        item_ids=[ex_reservation.item_id]
    )
    session = ex_reservation.exchange.get_ews_session()
    items = [item for item in gcir.send(session)]
    assert len(items) == 1, "Exchange returned %d items instead of 1" % (len(items))
    return str(etree.tostring(items[0], pretty_print=True), encoding='utf8')


@atomic
def sync_from_exchange(ex_resource, future_days=365, no_op=False):
    """
    Synchronize from Exchange to Respa

    Synchronizes current and future events for the given Exchange resource into
    the relevant Respa resource as reservations.

    :param ex_resource: The Exchange resource to sync
    :type ex_resource: respa_exchange.models.ExchangeResource
    :param future_days: How many days into the future to look
    :type future_days: int
    :param no_op: If True, do not save the reservations
    :type no_op: bool
    """
    if not ex_resource.sync_to_respa and not no_op:
        return
    start_date = now().replace(hour=0, minute=0, second=0)
    end_date = start_date + datetime.timedelta(days=future_days)

    log.info(
        "%s: Requesting items between (%s..%s)",
        ex_resource.principal_email,
        start_date,
        end_date
    )
    gcir = FindCalendarItemsRequest(
        principal=ex_resource.principal_email,
        start_date=start_date,
        end_date=end_date
    )
    session = ex_resource.exchange.get_ews_session()
    calendar_items = {}
    for item in gcir.send(session):
        calendar_items[ItemID.from_tree(item)] = item

    hashes = set(item_id.hash for item_id in calendar_items.keys())

    log.info(
        "%s: Received %d items",
        ex_resource.principal_email,
        len(calendar_items)
    )

    if no_op:
        return

    # First handle deletions . . .
    items_to_delete = ExchangeReservation.objects.select_related("reservation").filter(
        managed_in_exchange=True,  # Reservations we've downloaded ...
        reservation__begin__gte=start_date,  # that are in ...
        reservation__end__lte=end_date,  # ... our get items range ...
        reservation__resource__exchange_resource=ex_resource,  # and belong to this resource,
    ).exclude(item_id_hash__in=hashes)  # but aren't ones we're going to mangle

    for ex_reservation in items_to_delete:
        log.info("Deleting: %s", ex_reservation)
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
        item_props = _parse_item_props(ex_resource, item_id, item)

        if not ex_reservation:  # It's a new one!
            ex_reservation = _create_reservation_from_exchange(item_id, ex_resource, item_props)
        else:
            if ex_reservation._change_key != item_id.change_key:
                # Things changed, so edit the reservation
                _update_reservation_from_exchange(item_id, ex_reservation, ex_resource, item_props)

    log.info("%s: download processing complete", ex_resource.principal_email)
