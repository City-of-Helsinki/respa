from collections import defaultdict

from respa_exchange.ews.utils import format_date_for_xml
from respa_exchange.ews.xml import M, NAMESPACES, T


class CRUDItemHandlers(object):
    def __init__(self, item_id, change_key, update_change_key):
        self.item_id = item_id
        self.change_key = change_key
        self.update_change_key = update_change_key

    def _generate_items_fragment(self, change_key):
        return M.Items(
            T.CalendarItem(
                T.ItemId(
                    Id=self.item_id,
                    ChangeKey=change_key
                )
            )
        )

    def handle_create(self, request):
        # Handle CreateItem responses; always return success
        if not request.xpath("//m:CreateItem", namespaces=NAMESPACES):
            return  # pragma: no cover

        return M.CreateItemResponse(
            M.ResponseMessages(
                M.CreateItemResponseMessage(
                    {"ResponseClass": "Success"},
                    M.ResponseCode("NoError"),
                    self._generate_items_fragment(change_key=self.change_key)
                )
            )
        )

    def handle_delete(self, request):
        # Handle DeleteItem responses; always return success
        if not request.xpath("//m:DeleteItem", namespaces=NAMESPACES):
            return  # pragma: no cover
        return M.DeleteItemResponse(
            M.ResponseMessages(
                M.DeleteItemResponseMessage(
                    {"ResponseClass": "Success"},
                    M.ResponseCode("NoError"),
                )
            )
        )

    def handle_update(self, request):
        # Handle UpdateItem responses; return success
        if not request.xpath("//m:UpdateItem", namespaces=NAMESPACES):
            return  # pragma: no cover
        return M.UpdateItemResponse(
            M.ResponseMessages(
                M.UpdateItemResponseMessage(
                    {"ResponseClass": "Success"},
                    M.ResponseCode("NoError"),
                    self._generate_items_fragment(change_key=self.update_change_key),
                    M.ConflictResults(M.Count("0"))
                )
            )
        )


class FindItemsHandler(object):
    def __init__(self):
        self._email_to_props = defaultdict(dict)

    def handle_find_items(self, request):
        if not request.xpath("//m:FindItem", namespaces=NAMESPACES):
            return  # pragma: no cover
        email_address = request.xpath("//t:EmailAddress", namespaces=NAMESPACES)[0].text

        items = [
            self._generate_calendar_item(props)
            for props
            in self._email_to_props.get(email_address, {}).values()
        ]
        return M.FindItemResponse(
            M.ResponseMessages(
                M.FindItemResponseMessage(
                    {'ResponseClass': 'Success'},
                    M.ResponseCode('NoError'),
                    M.RootFolder(
                        {
                            'TotalItemsInView': str(len(items)),
                            'IncludesLastItemInRange': 'true',
                        },
                        T.Items(*items)
                    )
                )
            )
        )

    def handle_resolve_names(self, request):
        if not request.xpath("//m:ResolveNames", namespaces=NAMESPACES):
            return  # pragma: no cover
        ldap_address = request.xpath("//m:UnresolvedEntry", namespaces=NAMESPACES)[0].text
        assert ldap_address == '/O=Dummy'
        return M.ResolveNamesResponse(
            M.ResponseMessages(
                M.ResolveNamesResponseMessage(
                    {'ResponseClass': 'Success'},
                    M.ResponseCode('NoError'),
                    M.ResolutionSet(
                        {
                            'TotalItemsInView': '1',
                            'IncludesLastItemInRange': 'true',
                        },
                        T.Resolution(
                            T.Mailbox(
                                T.EmailAddress('dummy@example.com'),
                                T.RoutingType('SMTP'),
                                T.MailboxType('Mailbox')
                            ),
                            T.Contact(
                                T.DisplayName('Dummy Bob'),
                                T.GivenName('Bob'),
                                T.Surname('Dummy'),
                            )
                        )
                    )
                )
            )
        )

    def _generate_calendar_item(self, props):
        return T.CalendarItem(
            props['id'].to_xml(),
            T.Subject(props['subject']),
            T.HasAttachments('false'),
            T.IsAssociated('false'),
            T.Start(format_date_for_xml(props['start'])),
            T.End(format_date_for_xml(props['end'])),
            T.LegacyFreeBusyStatus('Busy'),
            T.Location(""),
            T.CalendarItemType('Single'),
            T.Organizer(
                T.Mailbox(
                    T.Name(props['organizer_name']),
                    T.EmailAddress('/O=Dummy'),
                    T.RoutingType('EX'),
                    T.MailboxType('OneOff')
                )
            )
        )

    def add_item(self, email, props):
        self._email_to_props[email][props["id"]] = props

    def delete_item(self, email, id):
        self._email_to_props[email].pop(id, None)
