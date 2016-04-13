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


class CreateCalendarItemRequest(EWSRequest):
    def __init__(
        self,
        principal,
        start,
        end,
        subject,
        body="",
        location="",
    ):
        # See http://msdn.microsoft.com/en-us/library/aa564690(v=exchg.140).aspx

        calendar_node = T.CalendarItem(
            T.Subject(subject),
            T.Body(body, BodyType="HTML"),
            T.ReminderIsSet('false'),
            T.Start(format_date_for_xml(start)),
            T.End(format_date_for_xml(end)),
            T.IsAllDayEvent('false'),
            T.Location(location)

        )
        root = M.CreateItem(
            M.SavedItemFolderId(get_distinguished_folder_id_element(principal, "calendar")),
            M.Items(calendar_node),
            SendMeetingInvitations="SendToAllAndSaveCopy"
        )
        super(CreateCalendarItemRequest, self).__init__(body=root, impersonation=principal)

    def send(self, sess):
        """
        Send the item creation request and return the Item ID object (for further manipulation)

        :type sess: respa_exchange.session.ExchangeSession
        :rtype: ItemID
        """
        return ItemID.from_tree(sess.soap(self))


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
