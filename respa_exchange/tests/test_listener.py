import pytest
from django.utils.crypto import get_random_string
from django.utils.timezone import now

from respa_exchange import listener
from respa_exchange.ews.xml import M, NAMESPACES, T
from respa_exchange.models import ExchangeResource
from respa_exchange.tests.session import SoapSeller


class SubscriptionHandler(object):
    """
    SoapSeller handler for the streaming requests.
    """

    def __init__(self, resource):
        self.resource = resource
        self.subscription_to_resource = {}

    def handle_subscribe(self, request):
        if not request.xpath('//m:StreamingSubscriptionRequest', namespaces=NAMESPACES):  # pragma: no cover
            return
        emails = request.xpath('//t:EmailAddress', namespaces=NAMESPACES)
        assert len(emails) == 1
        assert emails[0].text == self.resource.principal_email
        subscription_id = get_random_string(10)
        self.subscription_to_resource[subscription_id] = self.resource
        return M.SubscribeResponse(
            M.ResponseMessages(
                M.SubscribeResponseMessage(
                    M.ResponseCode('NoError'),
                    M.SubscriptionId(subscription_id),
                    ResponseClass='Success',
                ),
            ),
        )

    def _generate_event(self, type):
        return getattr(T, type)(
            T.TimeStamp(now().isoformat()),
            T.ItemId(
                Id=get_random_string(),
                ChangeKey=get_random_string(),
            ),
            T.ParentFolderId(
                Id=get_random_string(),
                ChangeKey=get_random_string(),
            ),
        )

    def handle_get_events(self, request):
        if not request.xpath('//m:GetStreamingEvents', namespaces=NAMESPACES):  # pragma: no cover
            return
        sub_id = request.xpath('//t:SubscriptionId', namespaces=NAMESPACES)[0].text
        # This would be a long-polling operation,
        # but ain't nobody got time for that
        return M.GetStreamingEventsResponse(
            M.ResponseMessages(
                M.GetStreamingEventsResponseMessage(
                    M.ResponseCode('NoError'),
                    M.Notifications(
                        M.Notification(
                            T.SubscriptionId(sub_id),
                            self._generate_event('NewMailEvent'),
                        ),
                    ),
                    ResponseClass='Success',
                ),
            ),
        )

    def handle_unsubscribe(self, request):
        if not request.xpath('//m:Unsubscribe', namespaces=NAMESPACES):  # pragma: no cover
            return
        subscription_id = request.xpath('//m:SubscriptionId', namespaces=NAMESPACES)[0].text
        self.subscription_to_resource.pop(subscription_id)
        return M.UnsubscribeResponse(
            M.ResponseMessages(
                M.UnsubscribeResponseMessage(
                    M.ResponseCode('NoError'),
                    ResponseClass='Success',
                ),
            ),
        )


@pytest.mark.django_db
def test_listener(settings, space_resource, exchange, monkeypatch):
    email = '%s@example.com' % get_random_string()
    ex_resource = ExchangeResource.objects.create(
        resource=space_resource,
        principal_email=email,
        exchange=exchange,
        sync_to_respa=True,
    )
    assert ex_resource.reservations.count() == 0
    delegate = SubscriptionHandler(ex_resource)
    SoapSeller.wire(settings, delegate)

    notification_listener = listener.NotificationListener()

    synced_resources = []  # Keep track of the resources we get sync-request events for

    def sync_resource(resource):  # Our pretend sync handler
        synced_resources.append(resource)
        # Ask the listener to stop after we get a resource,
        # so this test actually ends someday:
        notification_listener.stop()

    monkeypatch.setattr(listener, 'sync_from_exchange', sync_resource)
    notification_listener.start()
    # ... so when `sync_resource` is called, this'll eventually happen:
    assert ex_resource in synced_resources
