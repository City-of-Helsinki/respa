from .base import EWSRequest
from .folders import get_distinguished_folder_id_element
from .objs import ItemID
from .utils import format_date_for_xml
from .xml import M, NAMESPACES, T


class FindCalendarItemsRequest(EWSRequest):
    """
    An EWS request to request the calendar items for a given principal's calendar folder.
    """

    def __init__(self, principal, start_date, end_date):
        """
        Initialize the request.

        start_date and end_date should be kept sanely close to each other to avoid EWS erroring out.

        :param principal: The principal email whose calendar to query.
        :param start_date: Start date for the query
        :param end_date: End date for the query
        """
        body = M.FindItem(
            {'Traversal': 'Shallow'},
            M.ItemShape(
                T.BaseShape("Default")
            ),
            M.CalendarView({
                'MaxEntriesReturned': str(1048576),
                'StartDate': format_date_for_xml(start_date),
                'EndDate': format_date_for_xml(end_date),
            }),
            M.ParentFolderIds(get_distinguished_folder_id_element(principal, "calendar")),
        )
        super().__init__(body, impersonation=principal)

    def send(self, sess):
        """
        Send the calendar item request, and return a list of CalendarItem XML elements.

        :type sess: respa_exchange.session.ExchangeSession
        :rtype: list[lxml.etree.Element]
        """
        resp = sess.soap(self)
        return resp.xpath("//t:CalendarItem", namespaces=NAMESPACES)


class GetCalendarItemsRequest(EWSRequest):
    """
    An EWS request to request the detailed information about given items.
    """

    def __init__(self, principal, item_ids):
        """
        Initialize the request.

        :param principal: The principal email whose calendar to query.
        :param item_ids: Item IDs for the requested calendar items.
        """

        body = M.GetItem(
            M.ItemShape(
                T.BaseShape("AllProperties"),
                T.BodyType("HTML"),
            ),
            M.ItemIds(*[T.ItemId(dict(Id=i.id, ChangeKey=i.change_key)) for i in item_ids]),
        )
        super().__init__(body, impersonation=principal)

    def send(self, sess):
        """
        Send the calendar item request, and return a list of CalendarItem XML elements.

        :type sess: respa_exchange.session.ExchangeSession
        :rtype: list[lxml.etree.Element]
        """
        resp = sess.soap(self)
        return resp.xpath("//t:CalendarItem", namespaces=NAMESPACES)


class BaseCalendarItemRequest(EWSRequest):
    """
    Base class for requests somehow manipulating calendar items.

    Manages converting Pythonic property bags to XML form.
    """

    PROP_MAP = [  # The order is significant.
        ("subject", ("item:Subject", (lambda value: T.Subject(value)))),
        ("body", ("item:Body", (lambda value: T.Body(value, BodyType="Text")))),
        ("reminder", ("item:ReminderIsSet", (lambda value: T.ReminderIsSet(str(bool(value)).lower())))),
        ("start", ("calendar:Start", (lambda value: T.Start(format_date_for_xml(value))))),
        ("end", ("calendar:End", (lambda value: T.End(format_date_for_xml(value))))),
        ("all_day", ("calendar:IsAllDayEvent", (lambda value: T.IsAllDayEvent(str(bool(value)).lower())))),
        ("location", ("calendar:Location", (lambda value: T.Location(value)))),
        ("required_attendees", ("calendar:RequiredAttendees", (
            lambda value: T.RequiredAttendees(*[T.Attendee(T.Mailbox(T.EmailAddress(str(x)))) for x in value])))),
    ]
    PROP_DEFAULTS = {
        "all_day": False,
        "reminder": False,
    }

    def _convert_props(
        self,
        props,
        add_defaults=False,
    ):
        """
        Convert a calendar property bag to an iterable of (field_uri, Node) tuples.

        None values in props are ignored.

        :type props: dict[str, object]
        :rtype: Iterable[tuple[str, object]]
        """
        if add_defaults:
            props = dict(self.PROP_DEFAULTS, **props)
        for key, (field_uri, node_ctor) in self.PROP_MAP:
            value = props.get(key)
            if value is None:
                continue
            yield (field_uri, node_ctor(value))

    def send(self, sess):
        """
        Send the item manipulation request and return the Item ID object (for further manipulation)

        :type sess: respa_exchange.session.ExchangeSession
        :rtype: ItemID
        """
        return ItemID.from_tree(sess.soap(self))


class CreateCalendarItemRequest(BaseCalendarItemRequest):
    """
    Encapsulates a request to create a calendar item.
    """

    def __init__(
        self,
        principal,
        item_props,
        send_notifications=True,
    ):
        """
        Initialize the request.

        :param principal: Principal email to impersonate
        :type principal: str
        :param item_props: Dict of calendar item properties
        :type item_props: dict[str, object]
        """
        # See http://msdn.microsoft.com/en-us/library/aa564690(v=exchg.140).aspx

        fields = [
            node
            for (field_id, node)
            in self._convert_props(item_props, add_defaults=True)
        ]
        if send_notifications:
            send_notifications_string = "SendToAllAndSaveCopy"
        else:
            send_notifications_string = "SendToNone"

        root = M.CreateItem(
            M.SavedItemFolderId(get_distinguished_folder_id_element(principal, "calendar")),
            M.Items(T.CalendarItem(*fields)),
            SendMeetingInvitations=send_notifications_string
        )
        super(CreateCalendarItemRequest, self).__init__(body=root, impersonation=principal)


class UpdateCalendarItemRequest(BaseCalendarItemRequest):
    """
    Encapsulates a request to update an existing calendar item.
    """

    def __init__(
        self,
        principal,
        item_id,
        update_props,
        send_notifications=True,
    ):
        """
        Initialize the request.

        :param principal: Principal email to impersonate
        :type principal: str
        :param item_id: Item ID object
        :type item_id: respa_exchange.objs.ItemID
        :param update_props: Dict of properties to update
        :type update_props: dict[str, object]
        """
        updates = []
        for field_uri, node in self._convert_props(update_props):
            updates.append(T.SetItemField(
                T.FieldURI(FieldURI=field_uri),
                T.CalendarItem(node)
            ))
        if not updates:
            raise ValueError("No updates")

        if send_notifications:
            send_notifications_string = "SendToAllAndSaveCopy"
        else:
            send_notifications_string = "SendToNone"
        root = M.UpdateItem(
            M.ItemChanges(
                T.ItemChange(
                    item_id.to_xml(),
                    T.Updates(*updates)
                )
            ),
            ConflictResolution="AlwaysOverwrite",
            MessageDisposition="SendAndSaveCopy",
            SendMeetingInvitationsOrCancellations=send_notifications_string
        )

        super(UpdateCalendarItemRequest, self).__init__(root, impersonation=principal)


class DeleteCalendarItemRequest(EWSRequest):
    """
    Encapsulates a request to delete an existing calendar item.
    """

    def __init__(
        self,
        principal,
        item_id,
        send_notifications=True,
    ):
        """
        Initialize the request.

        :param principal: Principal email to impersonate
        :param item_id: Item ID object
        :type item_id: respa_exchange.objs.ItemID
        """
        if send_notifications:
            send_notifications_string = "SendToAllAndSaveCopy"
        else:
            send_notifications_string = "SendToNone"
        root = M.DeleteItem(
            M.ItemIds(item_id.to_xml()),
            DeleteType="HardDelete",
            SendMeetingCancellations=send_notifications_string,
            AffectedTaskOccurrences="AllOccurrences"
        )
        super(DeleteCalendarItemRequest, self).__init__(root, impersonation=principal)

    def send(self, sess):
        """
        Send the deletion request.

        :type sess: respa_exchange.session.ExchangeSession
        :return: True if the deletion was successful
        """
        resp = sess.soap(self)
        dirm = resp.find("*//m:DeleteItemResponseMessage", namespaces=NAMESPACES)
        return dirm.attrib["ResponseClass"] == "Success"
