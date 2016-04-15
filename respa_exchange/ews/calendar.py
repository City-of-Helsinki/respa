from .base import EWSRequest
from .folders import get_distinguished_folder_id_element
from .objs import ItemID
from .utils import format_date_for_xml
from .xml import M, NAMESPACES, T


class GetCalendarItemsRequest(EWSRequest):
    """
    An EWS request to request the calendar items for a given principal's calendar folder.
    """

    def __init__(self, principal, start_date, end_date):
        body = M.FindItem(
            {u'Traversal': u'Shallow'},
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
        super(GetCalendarItemsRequest, self).__init__(body, impersonation=principal)

    def send(self, sess):
        """
        Send the calendar item request, and return a list of CalendarItem XML elements.

        :type sess: respa_exchange.session.ExchangeSession
        :rtype: list[lxml.etree.Element]
        """
        resp = sess.soap(self)
        return resp.xpath("//t:CalendarItem", namespaces=NAMESPACES)


class BaseCalendarItemRequest(EWSRequest):
    PROP_MAP = [  # The order is significant.
        ("subject", ("item:Subject", (lambda value: T.Subject(value)))),
        ("body", ("item:Body", (lambda value: T.Body(value, BodyType="HTML")))),
        ("reminder", ("item:ReminderIsSet", (lambda value: T.ReminderIsSet(str(bool(value)).lower())))),
        ("start", ("calendar:Start", (lambda value: T.Start(format_date_for_xml(value))))),
        ("end", ("calendar:End", (lambda value: T.End(format_date_for_xml(value))))),
        ("all_day", ("calendar:IsAllDayEvent", (lambda value: T.IsAllDayEvent(str(bool(value)).lower())))),
        ("location", ("calendar:Location", (lambda value: T.Location(value)))),
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
    def __init__(
        self,
        principal,
        item_props
    ):
        """
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
        root = M.CreateItem(
            M.SavedItemFolderId(get_distinguished_folder_id_element(principal, "calendar")),
            M.Items(T.CalendarItem(*fields)),
            SendMeetingInvitations="SendToAllAndSaveCopy"
        )
        super(CreateCalendarItemRequest, self).__init__(body=root, impersonation=principal)


class UpdateCalendarItemRequest(BaseCalendarItemRequest):
    def __init__(
        self,
        principal,
        item_id,
        update_props
    ):
        """
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

        root = M.UpdateItem(
            M.ItemChanges(
                T.ItemChange(
                    item_id.to_xml(),
                    T.Updates(*updates)
                )
            ),
            ConflictResolution=u"AlwaysOverwrite",
            MessageDisposition=u"SendAndSaveCopy",
            SendMeetingInvitationsOrCancellations="SendToAllAndSaveCopy"
        )

        super(UpdateCalendarItemRequest, self).__init__(root, impersonation=principal)


class DeleteCalendarItemRequest(EWSRequest):
    def __init__(
        self,
        principal,
        item_id
    ):
        """
        :param principal: Principal email to impersonate
        :param item_id: Item ID object
        :type item_id: respa_exchange.objs.ItemID
        """
        root = M.DeleteItem(
            M.ItemIds(item_id.to_xml()),
            DeleteType="HardDelete",
            SendMeetingCancellations="SendToAllAndSaveCopy",
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
