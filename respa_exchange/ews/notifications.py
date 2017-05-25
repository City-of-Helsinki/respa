from lxml import etree

from respa_exchange.ews.base import EWSRequest
from respa_exchange.ews.folders import get_distinguished_folder_id_element
from respa_exchange.ews.xml import M, NAMESPACES, T


class StreamingEventError(Exception):
    def __init__(self, message, code):
        super(StreamingEventError, self).__init__('%s [%s]' % (message, code))
        self.message = message
        self.code = code

    @classmethod
    def from_response_message(cls, el):
        return cls(
            message=el.find('m:MessageText', namespaces=NAMESPACES).text,
            code=el.find('m:ResponseCode', namespaces=NAMESPACES).text,
        )


class SubscribeRequest(EWSRequest):
    """
    Encapsulates a request to subscribe to a notification stream.

    See https://msdn.microsoft.com/en-us/library/office/dn458792(v=exchg.150).aspx
    """
    version = 'Exchange2013'

    def __init__(self, principal):
        """
        Initialize the request.

        :param principal: Principal email to impersonate
        """
        root = M.Subscribe(
            M.StreamingSubscriptionRequest(
                T.FolderIds(get_distinguished_folder_id_element(principal, 'calendar')),
                T.EventTypes(
                    T.EventType('NewMailEvent'),
                    T.EventType('CreatedEvent'),
                    T.EventType('DeletedEvent'),
                    T.EventType('ModifiedEvent'),
                    T.EventType('MovedEvent'),
                    T.EventType('CopiedEvent'),
                    T.EventType('FreeBusyChangedEvent'),
                ),
            )
        )
        super(SubscribeRequest, self).__init__(root, impersonation=principal)

    def send(self, sess):
        """
        Send the subscription request.

        :type sess: respa_exchange.session.ExchangeSession
        :return: Tuple with subscription ID and possible watermark
        """
        resp = sess.soap(self)
        srm = resp.find('*//m:SubscribeResponseMessage', namespaces=NAMESPACES)
        response_code_el = srm.find('m:ResponseCode', namespaces=NAMESPACES)
        if response_code_el.text != 'NoError':
            raise Exception(etree.tostring(srm))
        sub_id_el = srm.find('m:SubscriptionId', namespaces=NAMESPACES)
        watermark_el = srm.find('m:Watermark', namespaces=NAMESPACES)
        if watermark_el:
            watermark = watermark_el.text
        else:
            watermark = None
        return (sub_id_el.text, watermark)


class UnsubscribeRequest(EWSRequest):
    """
    Encapsulates a request to unsubscribe from a previously created notification stream.

    See https://msdn.microsoft.com/en-us/library/office/dn458792(v=exchg.150).aspx
    """
    version = 'Exchange2013'

    def __init__(self, principal, subscription_id):
        """
        Initialize the request.

        :param principal: Principal email to impersonate
        :param subscription_id: Subscription ID to get rid of
        """
        root = M.Unsubscribe(
            M.SubscriptionId(subscription_id)
        )
        super(UnsubscribeRequest, self).__init__(root, impersonation=principal)

    def send(self, sess):
        """
        Send the unsubscription request.

        :type sess: respa_exchange.session.ExchangeSession
        :return: True if the response class is "Success".
        :rtype: bool
        """
        resp = sess.soap(self)
        urm = resp.find('*//m:UnsubscribeResponseMessage', namespaces=NAMESPACES)
        return (urm is not None and urm.attrib.get('ResponseClass') == 'Success')


class StreamingEvent(object):
    def __init__(self, subscription_id, type, data, exchange=None, resource=None):
        """
        :param subscription_id: The subscription ID that yielded this Event.
        :type subscription_id: str
        :param type: The type of this event. TODO: Document better.
        :type type: str
        :param data: The event data.
        :type data: dict[str, str]
        :param exchange: The ExchangeSession for this event.
        :type exchange: respa_exchange.session.ExchangeSession
        :param resource: The Resource (if available) for this event
        :type resource: resources.models.Resource
        """
        self.subscription_id = subscription_id
        self.type = type
        self.data = data
        self.exchange = exchange
        self.resource = resource

    def __repr__(self):
        return '<StreamingEvent(%r)>' % vars(self)


class GetStreamingEventsRequest(EWSRequest):
    """
    Encapsulates a request to get events from a previously created notification stream.

    Note that this is a long-polling operation; `.send()` will take a long time if there
    are no events.

    See https://msdn.microsoft.com/en-us/library/office/dn458792(v=exchg.150).aspx
    """
    version = 'Exchange2013'

    def __init__(self, subscription_ids, timeout_minutes=30):
        """
        Initialize the request.

        :param principal: Principal email to impersonate
        :param subscription_id: Subscription ID to get rid of
        """
        self.timeout_minutes = timeout_minutes
        root = M.GetStreamingEvents(
            M.SubscriptionIds(*[T.SubscriptionId(x) for x in subscription_ids]),
            M.ConnectionTimeout(str(timeout_minutes)),
        )
        super(GetStreamingEventsRequest, self).__init__(root)

    def process_response(self, resp):
        gserm = resp.find('*//m:GetStreamingEventsResponseMessage', namespaces=NAMESPACES)

        if gserm.attrib['ResponseClass'] != 'Success':
            raise StreamingEventError.from_response_message(gserm)

        for notif in gserm.xpath('//m:Notification', namespaces=NAMESPACES):
            subscription_id = notif.find('t:SubscriptionId', namespaces=NAMESPACES).text
            for ev_tag in notif.getchildren():
                if not ev_tag.tag.endswith('Event'):
                    continue
                data_dict = {
                    attr.tag: (attr.text or dict(attr.items()))
                    for attr
                    in ev_tag.getchildren()
                }
                yield StreamingEvent(
                    subscription_id=subscription_id,
                    type=ev_tag.tag,
                    data=data_dict,
                )

    def send(self, sess):
        """
        Send the event request request [sic].

        Note that this is a long-polling operation; returning from this function
        may take up to `timeout_minutes` minutes.

        :type sess: respa_exchange.session.ExchangeSession
        :return: Iterable of StreamingEvents
        :rtype: list[respa_exchange.ews.notifications.StreamingEvent]
        """
        timeout = (self.timeout_minutes + 1) * 60
        for resp in sess.soap_stream(self, timeout=timeout):
            events = self.process_response(resp)
            for event in events:
                yield event
