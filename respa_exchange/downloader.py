"""
Download Exchange events into Respa as reservations.
"""
import datetime
import logging
import iso8601

from lxml import etree
from django.db.transaction import atomic
from django.utils.timezone import now

from sentry_sdk import configure_scope, push_scope, capture_message

from resources.models.reservation import Reservation
from respa_exchange.ews.calendar import GetCalendarItemsRequest, FindCalendarItemsRequest
from respa_exchange.ews.user import ResolveNamesRequest
from respa_exchange.ews.objs import ItemID
from respa_exchange.ews.xml import NAMESPACES
from respa_exchange.models import ExchangeReservation, ExchangeUser, \
    ExchangeUserX500Address, ExchangeResource

log = logging.getLogger(__name__)


def element_to_string(elem):
    return etree.tostring(elem, pretty_print=True, encoding=str)


def _populate_reservation(reservation, ex_resource, item_props, ex_reservation=None):
    """
    Populate a Reservation instance based on Exchange data

    :type reservation: resources.models.Reservation
    :type ex_resource: respa_exchange.models.ExchangeResource
    :type item_props: dict
    :return:
    """
    reservation.begin = item_props['start']
    reservation.end = item_props['end']
    reservation._from_exchange = True  # Set a flag to prevent immediate re-upload

    # If the reservation does not originate from Exchange, we don't
    # allow editing anything else except the begin and end times.
    if ex_reservation is not None and not ex_reservation.managed_in_exchange:
        return

    subject = item_props['subject']
    if subject is None:
        with push_scope() as scope:
            scope.level = 'warning'
            capture_message("Calendar item has empty subject")
        subject = ''
    reservation.event_subject = subject

    organizer = item_props.get('organizer')
    if organizer is not None:
        reservation.reserver_email_address = organizer.email_address
        if organizer.given_name and organizer.surname:
            name = '%s %s' % (organizer.given_name, organizer.surname)
        else:
            name = organizer.name
        reservation.reserver_name = name or ''
        reservation.host_name = reservation.reserver_name
    else:
        reserver_name = item_props.get('reserver_name') or ''
        reservation.reserver_name = reserver_name
        reservation.host_name = reserver_name

    comment_text = "Synchronized from Exchange %s" % ex_resource.exchange
    reservation.comments = comment_text


def _update_reservation_from_exchange(item_id, ex_reservation, ex_resource, item_props):
    reservation = ex_reservation.reservation
    _populate_reservation(reservation, ex_resource, item_props, ex_reservation)
    reservation.save()
    ex_reservation.item_id = item_id
    if not ex_reservation.managed_in_exchange:
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


def _find_exchange_user_by_mailbox(ex_resource, mailbox, last_updated_at=None):
    """Try to find the ExchangeUser entry matching the organizer XML element

    Matching is attempted based on the organizer's email address and
    their X500 addresses. If a match can't be found, a ResolveNamesRequest
    is sent and the ExchangeUser model is updated based on the response.
    """

    routing_type = mailbox.find("t:RoutingType", namespaces=NAMESPACES).text
    user_identifier = mailbox.find("t:EmailAddress", namespaces=NAMESPACES).text
    user_name = mailbox.find("t:Name", namespaces=NAMESPACES)
    if user_name is not None:
        user_name = user_name.text
    if routing_type == "SMTP":
        id_search_field = 'email_address'
        user_identifier = user_identifier.lower()
    elif routing_type == "EX":
        id_search_field = 'x500_addresses__address__iexact'
    else:
        with push_scope() as scope:
            scope.level = 'warning'
            scope.set_extra('mailbox', element_to_string(mailbox))
            capture_message('Unknown mailbox routing type')
        return None

    search_args = {id_search_field: user_identifier, 'exchange': ex_resource.exchange}
    try:
        ex_user = ExchangeUser.objects.get(**search_args)
    except ExchangeUser.DoesNotExist:
        ex_user = None

    # If the user name remains the same, all other info is probably okay as well.
    # If not, we might need to refresh the user info from EWS.
    if ex_user is not None:
        if user_name == ex_user.name:
            return ex_user

        # If the user name does not match, but we have updated
        # the user info after the calendar item was created,
        # everything is fine.
        if last_updated_at and ex_user.updated_at:
            if ex_user.updated_at > last_updated_at:
                return ex_user

    req = ResolveNamesRequest([user_identifier], principal=ex_resource.principal_email)
    resolutions = req.send(ex_resource.exchange.get_ews_session())

    x500_addresses = []
    if routing_type == 'EX':
        x500_addresses.append(user_identifier.upper())

    for res in resolutions:
        mb = res.find("t:Mailbox", namespaces=NAMESPACES)
        if mb is None:
            continue

        user_name = mb.find("t:Name", namespaces=NAMESPACES)
        if user_name is not None:
            user_name = user_name.text
        else:
            user_name = ''

        routing_type = mb.find("t:RoutingType", namespaces=NAMESPACES).text
        email = mb.find("t:EmailAddress", namespaces=NAMESPACES)
        contact = res.find("t:Contact", namespaces=NAMESPACES)
        if routing_type != "SMTP" or email is None or contact is None:
            log.error("Invalid response to ResolveNamesRequest (%s)" % user_identifier)
            return None

        for x in contact.xpath('t:EmailAddresses/t:Entry', namespaces=NAMESPACES):
            text = x.text.upper()
            if not text.startswith('X500:'):
                continue
            text = ':'.join(text.split(':')[1:])
            x500_addresses.append(text)

        props = dict(given_name=contact.find("t:GivenName", namespaces=NAMESPACES),
                     surname=contact.find("t:Surname", namespaces=NAMESPACES))
        # props['name'] = contact.find("t:DisplayName", namespaces=NAMESPACES),
        props = {k: v.text for k, v in props.items() if v is not None}
        email = email.text.lower()
        props['email_address'] = email
        props['name'] = user_name
        break
    else:
        return None

    # Try to find exuser again based on x500_addresses
    if ex_user is None and x500_addresses:
        for addr in x500_addresses:
            try:
                ex_user = ExchangeUser.objects.get(
                    exchange=ex_resource.exchange,
                    x500_addresses__address__iexact=addr
                )
                break
            except ExchangeUser.DoesNotExist:
                pass

    if ex_user is None and props.get('email_address'):
        ex_user = ExchangeUser.objects.filter(email_address=props.get('email_address')).first()

    # If no matches based on any identifiers are found, it is a new user.
    if ex_user is None:
        ex_user = ExchangeUser(exchange=ex_resource.exchange)

    for k, v in props.items():
        setattr(ex_user, k, v)

    ex_user.save()

    existing_x500_addresses = set([x.upper() for x in ex_user.x500_addresses.values_list('address', flat=True)])
    new_x500_addresses = set(x500_addresses) - existing_x500_addresses
    for addr in new_x500_addresses:
        ExchangeUserX500Address.objects.create(
            exchange=ex_resource.exchange,
            user=ex_user,
            address=addr
        )

    return ex_user


def _determine_organizer(ex_resource, calendar_item):
    item_updated_at = calendar_item.get('updated_at')
    organizer = calendar_item.find('t:Organizer', namespaces=NAMESPACES)
    if organizer is None:
        return None

    mailbox = organizer.find('t:Mailbox', namespaces=NAMESPACES)
    ex_user = _find_exchange_user_by_mailbox(ex_resource, mailbox, item_updated_at)
    if ex_user is None:
        return None

    if ex_user.email_address.lower() == ex_resource.principal_email.lower():
        # Sometimes the reservation appears to be made by the resource
        # itself. We do a bit of heuristics to try to determine the actual
        # organizer.
        required_attendees = calendar_item.find('t:RequiredAttendees', namespaces=NAMESPACES)
        if required_attendees is None:
            return None
        first_attendee = required_attendees.find('t:Attendee', namespaces=NAMESPACES)
        if first_attendee is None:
            return None
        mailbox = first_attendee.find('t:Mailbox', namespaces=NAMESPACES)
        ex_user = _find_exchange_user_by_mailbox(ex_resource, mailbox, item_updated_at)

    return ex_user


def _parse_item_props(ex_resource, item):
    item_props = dict(
        start=iso8601.parse_date(item.find('t:Start', namespaces=NAMESPACES).text),
        end=iso8601.parse_date(item.find('t:End', namespaces=NAMESPACES).text),
        subject=item.find('t:Subject', namespaces=NAMESPACES).text,
    )

    item_props['updated_at'] = None
    el = item.find('t:LastModifiedTime', namespaces=NAMESPACES)
    if el is not None:
        if el.text:
            item_props['updated_at'] = iso8601.parse_date(el.text)

    organizer = _determine_organizer(ex_resource, item)
    if organizer is None:
        # The DisplayTo field appears to usually (?) contain the
        # name of the reserver.
        reserver_name = None
        display_to = item.find('t:DisplayTo', namespaces=NAMESPACES)
        if display_to is not None:
            reserver_name = display_to.text
            if reserver_name and ';' in reserver_name:
                reserver_name = None
        if reserver_name:
            item_props['reserver_name'] = reserver_name

    item_props['organizer'] = organizer

    # Subjects often start with the organizer name, so we strip it
    if organizer is not None and organizer.name:
        s = organizer.name + ' '
        subject = item_props['subject']
        if subject and subject.startswith(s):
            item_props['subject'] = subject[len(s):]

    return item_props


def fetch_reservation_data(ex_reservation):
    ex_resource = ex_reservation.reservation.resource.exchange_resource
    gcir = GetCalendarItemsRequest(
        principal=ex_resource.principal_email,
        item_ids=[ex_reservation.item_id]
    )
    session = ex_reservation.exchange.get_ews_session()
    items = [item for item in gcir.send(session)]
    if len(items) == 0:
        return None

    assert len(items) == 1, "Exchange returned %d items instead of 1" % (len(items))
    return items[0]


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

    # To avoid race conditions with the Respa API processes, we lock the
    # resource on database level before starting sync.
    ex_resource = ExchangeResource.objects.select_for_update().get(id=ex_resource.id)

    if not ex_resource.sync_to_respa and not no_op:
        return
    start_date = now().replace(hour=0, minute=0, second=0)
    end_date = start_date + datetime.timedelta(days=future_days)

    with configure_scope() as scope:
        scope.set_extra('resource', str(ex_resource))

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
        with configure_scope() as scope:
            scope.remove_extra('resource')
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
        with configure_scope() as scope:
            # Send the raw XML to Sentry for better debugging
            scope.set_extra('item_xml', element_to_string(item))

        ex_reservation = extant_exchange_reservations.get(item_id.hash)

        item_props = _parse_item_props(ex_resource, item)

        if not ex_reservation:  # It's a new one!
            ex_reservation = _create_reservation_from_exchange(item_id, ex_resource, item_props)
        else:
            if ex_reservation._change_key != item_id.change_key:
                # Things changed, so edit the reservation
                _update_reservation_from_exchange(item_id, ex_reservation, ex_resource, item_props)

    with configure_scope() as scope:
        scope.remove_extra('item_xml')
        scope.remove_extra('resource')

    log.info("%s: download processing complete", ex_resource.principal_email)
