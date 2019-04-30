# -*- coding: utf-8 -*-
import logging
import datetime
import pytz

from django.utils import timezone
import django.contrib.postgres.fields as pgfields
from django.conf import settings
from django.contrib.gis.db import models
from django.utils import translation
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError
from django.db.models import Q
from psycopg2.extras import DateTimeTZRange

from notifications.models import NotificationTemplate, NotificationTemplateException, NotificationType
from resources.signals import (
    reservation_modified, reservation_confirmed, reservation_cancelled
)
from .base import ModifiableModel
from .resource import generate_access_code, validate_access_code
from .resource import Resource
from .utils import (
    get_dt, save_dt, is_valid_time_slot, humanize_duration, send_respa_mail,
    DEFAULT_LANG, localize_datetime, format_dt_range, build_reservations_ical_file
)

DEFAULT_TZ = pytz.timezone(settings.TIME_ZONE)

logger = logging.getLogger(__name__)

RESERVATION_EXTRA_FIELDS = ('reserver_name', 'reserver_phone_number', 'reserver_address_street', 'reserver_address_zip',
                            'reserver_address_city', 'billing_address_street', 'billing_address_zip',
                            'billing_address_city', 'company', 'event_description', 'event_subject', 'reserver_id',
                            'number_of_participants', 'participants', 'reserver_email_address', 'host_name')


class ReservationQuerySet(models.QuerySet):
    def current(self):
        return self.exclude(state__in=(Reservation.CANCELLED, Reservation.DENIED))

    def active(self):
        return self.filter(end__gte=timezone.now()).current()

    def overlaps(self, begin, end):
        qs = Q(begin__lt=end) & Q(end__gt=begin)
        return self.filter(qs)

    def for_date(self, date):
        if isinstance(date, str):
            date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
        else:
            assert isinstance(date, datetime.date)
        dt = datetime.datetime.combine(date, datetime.datetime.min.time())
        start_dt = DEFAULT_TZ.localize(dt)
        end_dt = start_dt + datetime.timedelta(days=1)
        return self.overlaps(start_dt, end_dt)

    def extra_fields_visible(self, user):
        # the following logic is also implemented in Reservation.are_extra_fields_visible()
        # so if this is changed that probably needs to be changed as well

        if not user.is_authenticated:
            return self.none()
        if user.is_superuser:
            return self

        allowed_resources = Resource.objects.with_perm('can_view_reservation_extra_fields', user)
        return self.filter(Q(user=user) | Q(resource__in=allowed_resources))

    def catering_orders_visible(self, user):
        if not user.is_authenticated:
            return self.none()
        if user.is_superuser:
            return self

        allowed_resources = Resource.objects.with_perm('can_view_reservation_catering_orders', user)
        return self.filter(Q(user=user) | Q(resource__in=allowed_resources))


class Reservation(ModifiableModel):
    CREATED = 'created'
    CANCELLED = 'cancelled'
    CONFIRMED = 'confirmed'
    DENIED = 'denied'
    REQUESTED = 'requested'
    STATE_CHOICES = (
        (CREATED, _('created')),
        (CANCELLED, _('cancelled')),
        (CONFIRMED, _('confirmed')),
        (DENIED, _('denied')),
        (REQUESTED, _('requested')),
    )

    resource = models.ForeignKey('Resource', verbose_name=_('Resource'), db_index=True, related_name='reservations',
                                 on_delete=models.PROTECT)
    begin = models.DateTimeField(verbose_name=_('Begin time'))
    end = models.DateTimeField(verbose_name=_('End time'))
    duration = pgfields.DateTimeRangeField(verbose_name=_('Length of reservation'), null=True,
                                           blank=True, db_index=True)
    comments = models.TextField(null=True, blank=True, verbose_name=_('Comments'))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('User'), null=True,
                             blank=True, db_index=True, on_delete=models.PROTECT)
    state = models.CharField(max_length=16, choices=STATE_CHOICES, verbose_name=_('State'), default=CREATED)
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('Approver'),
                                 related_name='approved_reservations', null=True, blank=True,
                                 on_delete=models.SET_NULL)
    staff_event = models.BooleanField(verbose_name=_('Is staff event'), default=False)

    # access-related fields
    access_code = models.CharField(verbose_name=_('Access code'), max_length=32, null=True, blank=True)

    # EXTRA FIELDS START HERE

    event_subject = models.CharField(max_length=200, verbose_name=_('Event subject'), blank=True)
    event_description = models.TextField(verbose_name=_('Event description'), blank=True)
    number_of_participants = models.PositiveSmallIntegerField(verbose_name=_('Number of participants'), blank=True,
                                                              null=True)
    participants = models.TextField(verbose_name=_('Participants'), blank=True)
    host_name = models.CharField(verbose_name=_('Host name'), max_length=100, blank=True)

    # extra detail fields for manually confirmed reservations
    reserver_name = models.CharField(verbose_name=_('Reserver name'), max_length=100, blank=True)
    reserver_id = models.CharField(verbose_name=_('Reserver ID (business or person)'), max_length=30, blank=True)
    reserver_email_address = models.EmailField(verbose_name=_('Reserver email address'), blank=True)
    reserver_phone_number = models.CharField(verbose_name=_('Reserver phone number'), max_length=30, blank=True)
    reserver_address_street = models.CharField(verbose_name=_('Reserver address street'), max_length=100, blank=True)
    reserver_address_zip = models.CharField(verbose_name=_('Reserver address zip'), max_length=30, blank=True)
    reserver_address_city = models.CharField(verbose_name=_('Reserver address city'), max_length=100, blank=True)
    company = models.CharField(verbose_name=_('Company'), max_length=100, blank=True)
    billing_address_street = models.CharField(verbose_name=_('Billing address street'), max_length=100, blank=True)
    billing_address_zip = models.CharField(verbose_name=_('Billing address zip'), max_length=30, blank=True)
    billing_address_city = models.CharField(verbose_name=_('Billing address city'), max_length=100, blank=True)

    # If the reservation was imported from another system, you can store the original ID in the field below.
    origin_id = models.CharField(verbose_name=_('Original ID'), max_length=50, editable=False, null=True)

    objects = ReservationQuerySet.as_manager()

    class Meta:
        verbose_name = _("reservation")
        verbose_name_plural = _("reservations")
        ordering = ('id',)

    def _save_dt(self, attr, dt):
        """
        Any DateTime object is converted to UTC time zone aware DateTime
        before save

        If there is no time zone on the object, resource's time zone will
        be assumed through its unit's time zone
        """
        save_dt(self, attr, dt, self.resource.unit.time_zone)

    def _get_dt(self, attr, tz):
        return get_dt(self, attr, tz)

    @property
    def begin_tz(self):
        return self.begin

    @begin_tz.setter
    def begin_tz(self, dt):
        self._save_dt('begin', dt)

    def get_begin_tz(self, tz):
        return self._get_dt("begin", tz)

    @property
    def end_tz(self):
        return self.end

    @end_tz.setter
    def end_tz(self, dt):
        """
        Any DateTime object is converted to UTC time zone aware DateTime
        before save

        If there is no time zone on the object, resource's time zone will
        be assumed through its unit's time zone
        """
        self._save_dt('end', dt)

    def get_end_tz(self, tz):
        return self._get_dt("end", tz)

    def is_active(self):
        return self.end >= timezone.now() and self.state not in (Reservation.CANCELLED, Reservation.DENIED)

    def is_own(self, user):
        if not (user and user.is_authenticated):
            return False
        return user == self.user

    def need_manual_confirmation(self):
        return self.resource.need_manual_confirmation

    def are_extra_fields_visible(self, user):
        # the following logic is used also implemented in ReservationQuerySet
        # so if this is changed that probably needs to be changed as well

        if self.is_own(user):
            return True
        return self.resource.can_view_reservation_extra_fields(user)

    def can_view_access_code(self, user):
        if self.is_own(user):
            return True
        return self.resource.can_view_access_codes(user)

    def set_state(self, new_state, user):
        # Make sure it is a known state
        assert new_state in (
            Reservation.REQUESTED, Reservation.CONFIRMED, Reservation.DENIED,
            Reservation.CANCELLED
        )

        old_state = self.state
        if new_state == old_state:
            if old_state == Reservation.CONFIRMED:
                reservation_modified.send(sender=self.__class__, instance=self,
                                          user=user)
            return

        if new_state == Reservation.CONFIRMED:
            self.approver = user
            reservation_confirmed.send(sender=self.__class__, instance=self,
                                       user=user)
        elif old_state == Reservation.CONFIRMED:
            self.approver = None

        user_is_staff = self.user is not None and self.user.is_staff

        # Notifications
        if new_state == Reservation.REQUESTED:
            self.send_reservation_requested_mail()
            self.send_reservation_requested_mail_to_officials()
        elif new_state == Reservation.CONFIRMED:
            if self.need_manual_confirmation():
                self.send_reservation_confirmed_mail()
            elif self.access_code:
                self.send_reservation_created_with_access_code_mail()
            else:
                if not user_is_staff:
                    # notifications are not sent from staff created reservations to avoid spam
                    self.send_reservation_created_mail()
        elif new_state == Reservation.DENIED:
            self.send_reservation_denied_mail()
        elif new_state == Reservation.CANCELLED:
            if user != self.user:
                self.send_reservation_cancelled_mail()
            reservation_cancelled.send(sender=self.__class__, instance=self,
                                       user=user)

        self.state = new_state
        self.save()

    def can_modify(self, user):
        if not user:
            return False

        # reservations that need manual confirmation and are confirmed cannot be
        # modified or cancelled without reservation approve permission
        cannot_approve = not self.resource.can_approve_reservations(user)
        if self.need_manual_confirmation() and self.state == Reservation.CONFIRMED and cannot_approve:
            return False

        return self.user == user or self.resource.can_modify_reservations(user)

    def can_add_comment(self, user):
        if self.is_own(user):
            return True
        return self.resource.can_access_reservation_comments(user)

    def can_view_field(self, user, field):
        if field not in RESERVATION_EXTRA_FIELDS:
            return True
        if self.is_own(user):
            return True
        return self.resource.can_view_reservation_extra_fields(user)

    def can_view_catering_orders(self, user):
        if self.is_own(user):
            return True
        return self.resource.can_view_catering_orders(user)

    def format_time(self):
        tz = self.resource.unit.get_tz()
        begin = self.begin.astimezone(tz)
        end = self.end.astimezone(tz)
        return format_dt_range(translation.get_language(), begin, end)

    def __str__(self):
        if self.state != Reservation.CONFIRMED:
            state_str = ' (%s)' % self.state
        else:
            state_str = ''
        return "%s: %s%s" % (self.format_time(), self.resource, state_str)

    def clean(self, **kwargs):
        """
        Check restrictions that are common to all reservations.

        If this reservation isn't yet saved and it will modify an existing reservation,
        the original reservation need to be provided in kwargs as 'original_reservation', so
        that it can be excluded when checking if the resource is available.
        """
        if self.end <= self.begin:
            raise ValidationError(_("You must end the reservation after it has begun"))

        # Check that begin and end times are on valid time slots.
        opening_hours = self.resource.get_opening_hours(self.begin.date(), self.end.date())
        for dt in (self.begin, self.end):
            days = opening_hours.get(dt.date(), [])
            day = next((day for day in days if day['opens'] is not None and day['opens'] <= dt <= day['closes']), None)
            if day and not is_valid_time_slot(dt, self.resource.slot_size, day['opens']):
                raise ValidationError(_("Begin and end time must match time slots"))

        original_reservation = self if self.pk else kwargs.get('original_reservation', None)
        if self.resource.check_reservation_collision(self.begin, self.end, original_reservation):
            raise ValidationError(_("The resource is already reserved for some of the period"))

        if (self.end - self.begin) < self.resource.min_period:
            raise ValidationError(_("The minimum reservation length is %(min_period)s") %
                                  {'min_period': humanize_duration(self.resource.min_period)})

        if self.access_code:
            validate_access_code(self.access_code, self.resource.access_code_type)

    def get_notification_context(self, language_code, user=None, notification_type=None):
        if not user:
            user = self.user
        with translation.override(language_code):
            reserver_name = self.reserver_name
            if not reserver_name and self.user and self.user.get_display_name():
                reserver_name = self.user.get_display_name()
            context = {
                'resource': self.resource.name,
                'begin': localize_datetime(self.begin),
                'end': localize_datetime(self.end),
                'begin_dt': self.begin,
                'end_dt': self.end,
                'time_range': self.format_time(),
                'number_of_participants': self.number_of_participants,
                'host_name': self.host_name,
                'reserver_name': reserver_name,
                'event_subject': self.event_subject,
            }
            if self.resource.unit:
                context['unit'] = self.resource.unit.name
                context['unit_id'] = self.resource.unit.id
            if self.can_view_access_code(user) and self.access_code:
                context['access_code'] = self.access_code

            if notification_type == NotificationType.RESERVATION_CONFIRMED:
                if self.resource.reservation_confirmed_notification_extra:
                    context['extra_content'] = self.resource.reservation_confirmed_notification_extra
            elif notification_type == NotificationType.RESERVATION_REQUESTED:
                if self.resource.reservation_requested_notification_extra:
                    context['extra_content'] = self.resource.reservation_requested_notification_extra

            # Get last main and ground plan images. Normally there shouldn't be more than one of each
            # of those images.
            images = self.resource.images.filter(type__in=('main', 'ground_plan')).order_by('-sort_order')
            main_image = next((i for i in images if i.type == 'main'), None)
            ground_plan_image = next((i for i in images if i.type == 'ground_plan'), None)

            if main_image:
                main_image_url = main_image.get_full_url()
                if main_image_url:
                    context['resource_main_image_url'] = main_image_url
            if ground_plan_image:
                ground_plan_image_url = ground_plan_image.get_full_url()
                if ground_plan_image_url:
                    context['resource_ground_plan_image_url'] = ground_plan_image_url

        return context

    def send_reservation_mail(self, notification_type, user=None, attachments=None):
        """
        Stuff common to all reservation related mails.

        If user isn't given use self.user.
        """
        try:
            notification_template = NotificationTemplate.objects.get(type=notification_type)
        except NotificationTemplate.DoesNotExist:
            return

        if user:
            email_address = user.email
        else:
            if not (self.reserver_email_address or self.user):
                return
            email_address = self.reserver_email_address or self.user.email
            user = self.user

        language = user.get_preferred_language() if user else DEFAULT_LANG
        context = self.get_notification_context(language, notification_type=notification_type)

        try:
            rendered_notification = notification_template.render(context, language)
        except NotificationTemplateException as e:
            logger.error(e, exc_info=True, extra={'user': user.uuid})
            return

        send_respa_mail(
            email_address,
            rendered_notification['subject'],
            rendered_notification['body'],
            rendered_notification['html_body'],
            attachments
        )

    def send_reservation_requested_mail(self):
        self.send_reservation_mail(NotificationType.RESERVATION_REQUESTED)

    def send_reservation_requested_mail_to_officials(self):
        notify_users = self.resource.get_users_with_perm('can_approve_reservation')
        if len(notify_users) > 100:
            raise Exception("Refusing to notify more than 100 users (%s)" % self)
        for user in notify_users:
            self.send_reservation_mail(NotificationType.RESERVATION_REQUESTED_OFFICIAL, user=user)

    def send_reservation_denied_mail(self):
        self.send_reservation_mail(NotificationType.RESERVATION_DENIED)

    def send_reservation_confirmed_mail(self):
        reservations = [self]
        ical_file = build_reservations_ical_file(reservations)
        attachment = ('reservation.ics', ical_file, 'text/calendar')
        self.send_reservation_mail(NotificationType.RESERVATION_CONFIRMED,
                                   attachments=[attachment])

    def send_reservation_cancelled_mail(self):
        self.send_reservation_mail(NotificationType.RESERVATION_CANCELLED)

    def send_reservation_created_mail(self):
        reservations = [self]
        ical_file = build_reservations_ical_file(reservations)
        attachment = 'reservation.ics', ical_file, 'text/calendar'
        self.send_reservation_mail(NotificationType.RESERVATION_CREATED,
                                   attachments=[attachment])

    def send_reservation_created_with_access_code_mail(self):
        reservations = [self]
        ical_file = build_reservations_ical_file(reservations)
        attachment = 'reservation.ics', ical_file, 'text/calendar'
        self.send_reservation_mail(NotificationType.RESERVATION_CREATED_WITH_ACCESS_CODE,
                                   attachments=[attachment])

    def send_access_code_created_mail(self):
        self.send_reservation_mail(NotificationType.RESERVATION_ACCESS_CODE_CREATED)

    def save(self, *args, **kwargs):
        self.duration = DateTimeTZRange(self.begin, self.end, '[)')

        if not self.access_code:
            access_code_type = self.resource.access_code_type
            if self.resource.is_access_code_enabled() and self.resource.generate_access_codes:
                self.access_code = generate_access_code(access_code_type)

        return super().save(*args, **kwargs)


class ReservationMetadataField(models.Model):
    field_name = models.CharField(max_length=100, verbose_name=_('Field name'), unique=True)

    class Meta:
        verbose_name = _('Reservation metadata field')
        verbose_name_plural = _('Reservation metadata fields')

    def __str__(self):
        return self.field_name


class ReservationMetadataSet(ModifiableModel):
    name = models.CharField(max_length=100, verbose_name=_('Name'), unique=True)
    supported_fields = models.ManyToManyField(ReservationMetadataField, verbose_name=_('Supported fields'),
                                              related_name='metadata_sets_supported')
    required_fields = models.ManyToManyField(ReservationMetadataField, verbose_name=_('Required fields'),
                                             related_name='metadata_sets_required', blank=True)

    class Meta:
        verbose_name = _('Reservation metadata set')
        verbose_name_plural = _('Reservation metadata sets')

    def __str__(self):
        return self.name
