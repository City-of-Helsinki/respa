import logging
import threading
import time
from queue import Empty, Queue

from django.db import connections

from respa_exchange.downloader import sync_from_exchange
from respa_exchange.ews.notifications import (
    GetStreamingEventsRequest, StreamingEventError, SubscribeRequest, UnsubscribeRequest
)
from respa_exchange.ews.session import SoapFault
from respa_exchange.management.base import get_active_download_resources
from respa_exchange.models import ExchangeConfiguration
from respa_exchange.utils.timeout import EventedTimeout

log = logging.getLogger('respa_exchange.listener')


class EventAwaiterThread(threading.Thread):
    """
    A thread that makes long-polling GetStreamingEventsRequests until told to stop (or if many errors occur).
    """

    def __init__(self, event_callback, resource, subscription_id, timeout_minutes=15):
        """
        :param event_callback: A function to call when an event is received.
        :type event_callback: function[respa_exchange.ews.notifications.StreamingEvent]
        :param resource: The resource we're managing.
        :type resource: respa_exchange.models.Resource
        :param subscription_id: The EWS subscription ID to listen to notifications for.
        :type subscription_id: str
        :param timeout_minutes: How many minutes each GetStreamingEventsRequests is requested to live for.
                                The shorter this value, the easier the thread is to kill.
        :type timeout_minutes: int
        """
        assert callable(event_callback)
        self.event_callback = event_callback
        self.resource = resource
        self.subscription_id = subscription_id
        self.timeout_minutes = int(timeout_minutes)
        self.please_stop = False
        super(EventAwaiterThread, self).__init__(name="Listener-%s" % resource)

    def run(self):
        """Method representing the thread's activity. (See superclass.)"""
        sess = self.resource.exchange.get_ews_session()
        failures = 0
        while not self.please_stop:
            try:
                event_req = GetStreamingEventsRequest(
                    principal=self.resource.principal_email,
                    subscription_id=self.subscription_id,
                    timeout_minutes=self.timeout_minutes,
                )
                try:
                    for event in event_req.send(sess):
                        event.resource = self.resource  # We know the resource, so augment here.
                        self.event_callback(event)
                    time.sleep(0.5)
                except StreamingEventError as see:  # pragma: no cover
                    if see.code == 'ErrorSubscriptionNotFound':
                        log.info('Received ErrorSubscriptionNotFound for %s' % self.subscription_id)
                        break
                    raise
            except:  # pragma: no cover
                log.warn('Error in %s', self, exc_info=True)
                failures += 1
                if failures >= 10:
                    log.warn('Killing off %s, too many failures', self)
                    self.please_stop = True
        log.info('Event thread %s dying', self)


class NotificationListener(object):
    """
    This class manages a number of threads that hold long-poll connections.
    """

    SUBSCRIPTION_MANAGE_INTERVAL = 60
    DATABASE_RECONNECT_INTERVAL = 1800

    def __init__(self):
        self.exchanges = ExchangeConfiguration.objects.filter(enabled=True)
        self.resource_to_subscription_map = {}
        self.subscription_to_thread_map = {}
        self.events = Queue()
        self.subscription_manage_timer = EventedTimeout(
            seconds=self.SUBSCRIPTION_MANAGE_INTERVAL,
            on_timeout=self.manage_subscriptions,
        )
        self.database_reconnect_timer = EventedTimeout(
            seconds=self.DATABASE_RECONNECT_INTERVAL,
            on_timeout=self.reconnect_database,
        )
        self._please_stop = False

    def start(self):
        """
        Start the listener.

        This method will not return unless an unexpected exception occurs,
        or if `.stop()` is called (likely from another thread of control).
        """
        self.subscription_manage_timer.reset()
        self.database_reconnect_timer.reset()
        self.manage_subscriptions()
        self._please_stop = False

        log.debug('Starting loop.')

        try:
            while not self._please_stop:
                self.step()
                time.sleep(1)
        finally:
            self.close()

    def stop(self):
        """
        Stop the listener, if it's active.

        In bad situations, this might not actually do anything, though.
        """
        self._please_stop = True

    def step(self):
        """
        Run a single step of the listener management loop.

        This is a semi-public API; you shouldn't need to have to call
        this unless you're reimplementing the `.start()` loop yourself.
        """
        self.subscription_manage_timer.check()
        self.database_reconnect_timer.check()
        self.reap_threads()
        self.spawn_threads()
        self.handle_events()

    def post_event(self, event):
        """
        Post an event into the listener's event queue.
        (The queue is drained by `handle_events`.)

        This is the API by which respa_exchange.listener.EventAwaiterThread
        objects interface with the listener.

        If you are subclassing NotificationListener, this would be a
        spectacularly good place to preprocess events.

        :param event: The event that was received.
        :type event: respa_exchange.ews.notifications.StreamingEvent
        """
        self.events.put(event)
        log.debug('Event received: %s', event)

    def reconnect_database(self):
        """
        Reconnect all Django databases.

        This is run periodically to ensure we won't get "Database
        has gone away" or whatnot since we're holding an idle connection.
        """
        for conn in connections.all():
            try:
                conn.connect()
            except:
                log.exception('Failed reconnecting %s', conn)

    def manage_subscriptions(self):
        """
        Ensure the subscription map is up to date.

        This is called periodically by the `subscription_manage_timer` timeout.
        """
        resources = set(get_active_download_resources(exchange_configs=self.exchanges))
        new_resources = set(resources) - set(self.resource_to_subscription_map)
        gone_resources = set(self.resource_to_subscription_map) - set(resources)
        for resource in gone_resources:
            try:
                log.debug('Unsubscribing %s', resource)
                self.unsubscribe_resource(resource)
            except SoapFault:  # pragma: no cover
                log.warn('Unsubscription for %s failed', resource, exc_info=True)

        for resource in new_resources:
            try:
                log.debug('Subscribing %s', resource)
                self.subscribe_resource(resource)
            except SoapFault:  # pragma: no cover
                log.warn('Subscription to %s failed', resource, exc_info=True)

    def subscribe_resource(self, resource):
        """
        Attempt to create an Exchange subscription for the given resource.

        :param resource: The resource to subscribe.
        :type resource: respa_exchange.models.Resource
        """
        sub = SubscribeRequest(resource.principal_email)
        sub_id = sub.send(resource.exchange.get_ews_session())
        self.resource_to_subscription_map[resource] = sub_id
        log.info('Subscribed to %s on channel %s', resource, sub_id)

    def unsubscribe_resource(self, resource):
        """
        Attempt to remove an existing Exchange subscription for the given resource.

        If we don't know about a subscription for that resource, nothing happens
        and False is returned.

        :param resource: The resource to subscribe.
        :type resource: respa_exchange.models.Resource
        :return: Whether or not an unsubscription attempt was made.
        :rtype: bool
        """

        sub_id = self.resource_to_subscription_map.pop(resource, None)
        if not sub_id:
            return False
        unsub = UnsubscribeRequest(resource.principal_email, sub_id)
        unsub.send(resource.exchange.get_ews_session())
        return True

    def spawn_threads(self):
        """
        Spawn event awaiter threads for newly created subscriptions.

        """
        for resource, subscription_id in self.resource_to_subscription_map.items():
            if subscription_id in self.subscription_to_thread_map:
                # We already have a thread for this subscription -- never mind!
                continue

            self.subscription_to_thread_map[subscription_id] = awaiter_thread = EventAwaiterThread(
                event_callback=self.post_event,
                resource=resource,
                subscription_id=subscription_id,
            )
            awaiter_thread.start()
            log.debug('Started new awaiter thread %s', awaiter_thread)

    def reap_threads(self):
        """
        Reap all threads that are somehow out of control.

        Out of control, in this context, means:

        * exited (i.e. too many errors, or something similar)
        * managing a subscription that we no longer care about
        """
        known_subscription_ids = set(self.resource_to_subscription_map.values())
        for subscription_id, thread in list(self.subscription_to_thread_map.items()):  # List to copy the pairs
            assert isinstance(thread, EventAwaiterThread)

            if subscription_id not in known_subscription_ids:
                log.debug('Abandoning wild thread %s (subid %s not known)', thread, subscription_id)
                thread.please_stop = True  # Try to tell the thread to stop when possible (no guarantee it'll listen)
                self.subscription_to_thread_map.pop(subscription_id, None)
                continue

            if not thread.is_alive():  # pragma: no cover
                log.debug('Reaped dead thread %s', thread)
                self.subscription_to_thread_map.pop(subscription_id, None)

    def close(self):
        """
        Close all related resources (unsubscribe in Exchange and reap threads).

        This is called automatically by `.start()` when the loop ends, but it should be
        safe to call from wherever.
        """
        for resource in list(self.resource_to_subscription_map.keys()):
            self.unsubscribe_resource(resource)
        self.reap_threads()

    def handle_events(self):
        """
        Process whatever events are in the event queue.

        Returns when the event queue is drained.
        """
        changed_resources = set()
        while True:
            try:
                event = self.events.get(block=False)
            except Empty:
                break

            if not event.resource:  # pragma: no cover
                log.warn('Unable to handle resourceless event %r', event)
                return
            # TODO: Maybe process different events in different ways? ->
            #       Right now, whatever happens we just re-sync everything.
            changed_resources.add(event.resource)
        for resource in changed_resources:
            sync_from_exchange(resource)
