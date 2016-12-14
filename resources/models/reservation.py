# -*- coding: utf-8 -*-
from django.utils import timezone
import django.contrib.postgres.fields as pgfields
from django.conf import settings
from django.contrib.gis.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError
from psycopg2.extras import DateTimeTZRange

from guardian.shortcuts import get_users_with_perms

from .base import ModifiableModel
from .resource import Resource, generate_access_code, validate_access_code
from .utils import get_dt, save_dt, is_valid_time_slot, humanize_duration, send_respa_mail, DEFAULT_LANG


RESERVATION_EXTRA_FIELDS = ('reserver_name', 'reserver_phone_number', 'reserver_address_street', 'reserver_address_zip',
                            'reserver_address_city', 'billing_address_street',  'billing_address_zip',
                            'billing_address_city', 'company', 'event_description', 'event_subject', 'reserver_id',
                            'number_of_participants', 'reserver_email_address', 'host_name')


class ReservationQuerySet(models.QuerySet):
    def active(self):
        return self.filter(end__gte=timezone.now()).exclude(state__in=(Reservation.CANCELLED, Reservation.DENIED))


class Reservation(ModifiableModel):
    CANCELLED = 'cancelled'
    CONFIRMED = 'confirmed'
    DENIED = 'denied'
    REQUESTED = 'requested'
    STATE_CHOICES = (
        (CANCELLED, _('cancelled')),
        (CONFIRMED, _('confirmed')),
        (DENIED, _('denied')),
        (REQUESTED, _('requested')),
    )

    resource = models.ForeignKey('Resource', verbose_name=_('Resource'), db_index=True, related_name='reservations')
    begin = models.DateTimeField(verbose_name=_('Begin time'))
    end = models.DateTimeField(verbose_name=_('End time'))
    duration = pgfields.DateTimeRangeField(verbose_name=_('Length of reservation'), null=True,
                                           blank=True, db_index=True)
    comments = models.TextField(null=True, blank=True, verbose_name=_('Comments'))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('User'), null=True,
                             blank=True, db_index=True)
    state = models.CharField(max_length=16, choices=STATE_CHOICES, verbose_name=_('State'), default=CONFIRMED)
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('Approver'),
                                 related_name='approved_reservations', null=True, blank=True)

    # access-related fields
    access_code = models.CharField(verbose_name=_('Access code'), max_length=32, null=True, blank=True)

    # EXTRA FIELDS START HERE

    event_subject = models.CharField(max_length=200, verbose_name=_('Event subject'), blank=True)
    event_description = models.TextField(verbose_name=_('Event description'), blank=True)
    number_of_participants = models.PositiveSmallIntegerField(verbose_name=_('Number of participants'), blank=True,
                                                              null=True)
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

    def need_manual_confirmation(self):
        return self.resource.need_manual_confirmation

    def are_extra_fields_visible(self, user):
        if not self.need_manual_confirmation():
            return True
        if not (user and user.is_authenticated()):
            return False
        return user == self.user or self.resource.is_admin(user)

    def can_view_access_code(self, user):
        return user == self.user or self.resource.can_view_access_codes(user)

    def set_state(self, new_state, user):
        if new_state == self.state:
            return

        if new_state == Reservation.CONFIRMED:
            self.approver = user
            if self.need_manual_confirmation():
                self.send_reservation_confirmed_mail()
        elif self.state == Reservation.CONFIRMED:
            self.approver = None

        if new_state == Reservation.DENIED:
            self.send_reservation_denied_mail()
        elif new_state == Reservation.CANCELLED:
            if user != self.user:
                self.send_reservation_cancelled_mail()

        self.state = new_state
        self.save()

    class Meta:
        verbose_name = _("reservation")
        verbose_name_plural = _("reservations")

    def __str__(self):
        return "%s -> %s: %s" % (self.begin, self.end, self.resource)

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
            if day and not is_valid_time_slot(dt, self.resource.min_period, day['opens']):
                raise ValidationError(_("Begin and end time must match time slots"))

        original_reservation = self if self.pk else kwargs.get('original_reservation', None)
        if self.resource.check_reservation_collision(self.begin, self.end, original_reservation):
            raise ValidationError(_("The resource is already reserved for some of the period"))

        if (self.end - self.begin) < self.resource.min_period:
            raise ValidationError(_("The minimum reservation length is %(min_period)s") %
                                  {'min_period': humanize_duration(self.min_period)})

        if self.access_code:
            validate_access_code(self.access_code, self.resource.access_code_type)

    def send_reservation_mail(self, subject, template_name, extra_context=None, user=None):
        """
        Stuff common to all reservation related mails.

        If user isn't given use self.user.
        """

        if user:
            email_address = user.email
        else:
            if not (self.reserver_email_address or self.user):
                return
            email_address = self.reserver_email_address or self.user.email
            user = self.user
        language = user.get_preferred_language() if user else DEFAULT_LANG

        context = {'reservation': self}
        if extra_context:
            context.update(extra_context)
        send_respa_mail(email_address, subject, template_name, context, language)

    def send_reservation_requested_mail(self):
        self.send_reservation_mail(_("You've made a preliminary reservation"), 'reservation_requested')

    def send_reservation_requested_mail_to_officials(self):
        unit = self.resource.unit
        for user in get_users_with_perms(unit):
            if user.has_perm('can_approve_reservation', unit):
                self.send_reservation_mail(_('Reservation requested'), 'reservation_requested_official', user=user)

    def send_reservation_denied_mail(self):
        self.send_reservation_mail(_('Reservation denied'), 'reservation_denied')

    def send_reservation_confirmed_mail(self):
        self.send_reservation_mail(_('Reservation confirmed'), 'reservation_confirmed')

    def send_reservation_cancelled_mail(self):
        self.send_reservation_mail(_('Reservation cancelled'), 'reservation_cancelled')

    def send_reservation_created_with_access_code_mail(self):
        self.send_reservation_mail(_('Reservation created'), 'reservation_created_with_access_code')

    def save(self, *args, **kwargs):
        self.duration = DateTimeTZRange(self.begin, self.end, '[)')

        access_code_type = self.resource.access_code_type
        if not self.resource.is_access_code_enabled():
            self.access_code = ''
        elif not self.access_code:
            self.access_code = generate_access_code(access_code_type)

        return super().save(*args, **kwargs)

    objects = ReservationQuerySet.as_manager()


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
