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


class SyncEvent:
    def __init__(self, resource):
        self.resource = resource


class ThreadDyingEvent:
    def __init__(self):
        self.resource = None


class EventAwaiterThread(threading.Thread):
    """
    A thread that makes long-polling GetStreamingEventsRequests until told to stop (or if many errors occur).
    """

    def __init__(self, event_callback, exchange, subscription_ids, timeout_minutes=20):
        """
        :param event_callback: A function to call when an event is received.
        :type event_callback: function[respa_exchange.ews.notifications.StreamingEvent]
        :param exchange: The Exchange configuration the thread is bound to
        :type exchange: respa_exchange.models.ExchangeConfiguration
        :param subscription_ids: The subscriptions we're managing.
        :type subscription_ids: list
        :param timeout_minutes: How many minutes each GetStreamingEventsRequests is requested to live for.
                                The shorter this value, the easier the thread is to kill.
        :type timeout_minutes: int
        """
        assert callable(event_callback)
        self.event_callback = event_callback
        self.exchange = exchange
        self.subscription_ids = subscription_ids
        self.timeout_minutes = int(timeout_minutes)
        self.please_stop = False
        self.dead = False
        super(EventAwaiterThread, self).__init__(name="Listener-%s" % exchange)

    def run(self):
        """Method representing the thread's activity. (See superclass.)"""
        sess = self.exchange.get_ews_session()
        failures = 0
        last_loop_time = 0
        while not self.please_stop:
            try:
                event_req = GetStreamingEventsRequest(
                    subscription_ids=self.subscription_ids,
                    timeout_minutes=self.timeout_minutes,
                )
                try:
                    # Make sure we don't overwhelm the server with requests.
                    now = time.time()
                    if now - last_loop_time < 1:
                        time.sleep(1 - (now - last_loop_time))
                    last_loop_time = now

                    for event in event_req.send(sess):
                        if self.please_stop:
                            break
                        self.event_callback(event)
                        # Reset failure count when an event is successfully received.
                        failures = 0
                except StreamingEventError as see:  # pragma: no cover
                    if self.please_stop:
                        break
                    if see.code == 'ErrorSubscriptionNotFound':
                        log.info('Received ErrorSubscriptionNotFound for %s' % self.subscription_ids)
                        break
                    raise
            except Exception:  # pragma: no cover
                log.exception('Error in %s' % self)
                failures += 1
                if failures >= 5:
                    log.warn('Killing off %s, too many failures', self)
                    self.please_stop = True
                # For each failure, sleep a while so that we don't end up
                # bombarding the server with requests.
                time.sleep(failures ** 2.0)

        log.info('Event thread %s dying', self)
        self.dead = True
        self.event_callback(ThreadDyingEvent())
        failed_once = True

    def stop(self):
        self.please_stop = True


class ExchangeListener(object):
    def __init__(self, exchange, event_callback, sync_after_start=False):
        self.exchange = exchange
        self.event_callback = event_callback
        self.listener_thread = None
        self.resource_to_subscription_map = {}
        self.please_stop = False
        self.sync_after_start = sync_after_start

    def manage_subscriptions(self):
        """
        Ensure the subscription map is up to date.

        This is called periodically by the `subscription_manage_timer` timeout.
        """
        resources = set(get_active_download_resources(exchange_configs=[self.exchange]))
        new_resources = set(resources) - set(self.resource_to_subscription_map)
        gone_resources = set(self.resource_to_subscription_map) - set(resources)

        if not new_resources and not gone_resources:
            return

        if self.listener_thread:
            self.listener_thread.stop()
            self.listener_thread = None

        for resource in gone_resources:
            try:
                log.info('Resource %s removed, unsubscribing', resource)
                self.unsubscribe_resource(resource)
            except SoapFault:  # pragma: no cover
                log.warn('Unsubscription for %s failed', resource, exc_info=True)

        for resource in new_resources:
            try:
                log.info('Resource %s added, subscribing', resource)
                self.subscribe_resource(resource)
            except SoapFault:  # pragma: no cover
                log.warn('Subscription to %s failed', resource, exc_info=True)

        self.spawn_thread()
        if self.sync_after_start:
            for resource in resources:
                event = SyncEvent(resource=resource)
                self.event_callback(event)

    def subscribe_resource(self, resource):
        """
        Attempt to create an Exchange subscription for the given resource.

        :param resource: The resource to subscribe.
        :type resource: respa_exchange.models.Resource
        """
        assert self.exchange == resource.exchange
        sess = self.exchange.get_ews_session()
        sub = SubscribeRequest(resource.principal_email)
        sub_id, _ = sub.send(sess)
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

        assert self.exchange == resource.exchange
        sub_id = self.resource_to_subscription_map.pop(resource, None)
        if not sub_id:
            return False
        unsub = UnsubscribeRequest(resource.principal_email, sub_id)
        unsub.send(self.exchange.get_ews_session())
        log.info('Unsubscribed from %s on channel %s', resource, sub_id)
        return True

    def spawn_thread(self):
        """
        Spawn event awaiter thread for newly created subscriptions.
        """

        if self.listener_thread and not self.listener_thread.dead:
            return

        subscription_ids = self.resource_to_subscription_map.values()
        self.listener_thread = EventAwaiterThread(
            event_callback=self.post_event,
            exchange=self.exchange,
            subscription_ids=subscription_ids,
        )
        self.listener_thread.start()
        log.info('Started awaiter thread %s', self.listener_thread)

    def post_event(self, event):
        if self.please_stop:
            return
        if isinstance(event, ThreadDyingEvent):
            event.listener = self
            self.event_callback(event)
            return

        for resource, sub_id in self.resource_to_subscription_map.items():
            if sub_id == event.subscription_id:
                break
        else:
            log.warn('Unable to find subscription for event %r', event)
            return

        event.resource = resource
        self.event_callback(event)

    def start(self):
        self.manage_subscriptions()

    def close(self):
        """
        Close all related resources (unsubscribe in Exchange and reap threads).

        This is called automatically by `.start()` when the loop ends, but it should be
        safe to call from wherever.
        """
        self.please_stop = True
        self.listener_thread.stop()
        for resource in list(self.resource_to_subscription_map.keys()):
            self.unsubscribe_resource(resource)


class NotificationListener(object):
    """
    This class manages a number of threads that hold long-poll connections.
    """

    SUBSCRIPTION_MANAGE_INTERVAL = 180
    DATABASE_RECONNECT_INTERVAL = 1800

    def __init__(self, sync_after_start=False):
        exchanges = ExchangeConfiguration.objects.filter(enabled=True)
        self.sync_after_start = sync_after_start
        self.listeners = {ex: ExchangeListener(ex, self.post_event, sync_after_start) for ex in exchanges}
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
        self._please_stop = False

        log.debug('Starting listeners.')
        for listener in self.listeners.values():
            listener.start()

        log.debug('Starting loop.')
        try:
            while not self._please_stop:
                self.step()
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
        # handle_events() will sleep if no events are available
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
            except Exception:
                log.exception('Failed reconnecting %s', conn)

    def manage_subscriptions(self):
        for listener in self.listeners.values():
            listener.manage_subscriptions()

    def handle_events(self):
        """
        Process whatever events are in the event queue.

        Returns when the event queue is drained.
        """
        changed_resources = set()
        while True:
            try:
                event = self.events.get(timeout=1)
                if hasattr(self.events, 'task_done'):
                    self.events.task_done()
            except Empty:
                break

            if isinstance(event, ThreadDyingEvent):
                log.warn('Listener %s died, starting a new one' % event.listener)
                for ex, listener in self.listeners.items():
                    if event.listener != listener:
                        continue
                    listener.close()
                    listener = ExchangeListener(ex, self.post_event, self.sync_after_start)
                    self.listeners[ex] = listener
                    listener.start()
                    break
                return

            if not event.resource:  # pragma: no cover
                log.warn('Unable to handle resourceless event %r', event)
                return
            # TODO: Maybe process different events in different ways? ->
            #       Right now, whatever happens we just re-sync everything.
            changed_resources.add(event.resource)

        for resource in changed_resources:
            sync_from_exchange(resource)

    def close(self):
        for listener in self.listeners.values():
            listener.close()
        self.listeners.clear()
