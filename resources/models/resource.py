import datetime
import os
import re
import pytz
from collections import OrderedDict
from decimal import Decimal

import arrow
import django.db.models as dbm
from django.db.models import Q
from django.apps import apps
from django.conf import settings
from django.contrib.gis.db import models
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.validators import MinValueValidator
from django.urls import reverse
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.functional import cached_property
from django.utils.six import BytesIO
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import pgettext_lazy
from django.contrib.postgres.fields import HStoreField, DateTimeRangeField
from .gistindex import GistIndex
from psycopg2.extras import DateTimeTZRange
from image_cropping import ImageRatioField
from PIL import Image
from guardian.shortcuts import get_objects_for_user, get_users_with_perms
from guardian.core import ObjectPermissionChecker

from ..auth import is_authenticated_user, is_general_admin
from ..errors import InvalidImage
from ..fields import EquipmentField
from .base import AutoIdentifiedModel, NameIdentifiedModel, ModifiableModel
from .utils import create_datetime_days_from_now, get_translated, get_translated_name, humanize_duration
from .equipment import Equipment
from .unit import Unit
from .availability import get_opening_hours
from .permissions import RESOURCE_GROUP_PERMISSIONS


def generate_access_code(access_code_type):
    if access_code_type == Resource.ACCESS_CODE_TYPE_NONE:
        return ''
    elif access_code_type == Resource.ACCESS_CODE_TYPE_PIN4:
        return get_random_string(4, '0123456789')
    elif access_code_type == Resource.ACCESS_CODE_TYPE_PIN6:
        return get_random_string(6, '0123456789')
    else:
        raise NotImplementedError('Don\'t know how to generate an access code of type "%s"' % access_code_type)


def validate_access_code(access_code, access_code_type):
    if access_code_type == Resource.ACCESS_CODE_TYPE_NONE:
        return
    elif access_code_type == Resource.ACCESS_CODE_TYPE_PIN4:
        if not re.match('^[0-9]{4}$', access_code):
            raise ValidationError(dict(access_code=_('Invalid value')))
    elif access_code_type == Resource.ACCESS_CODE_TYPE_PIN6:
        if not re.match('^[0-9]{6}$', access_code):
            raise ValidationError(dict(access_code=_('Invalid value')))
    else:
        raise NotImplementedError('Don\'t know how to validate an access code of type "%s"' % access_code_type)

    return access_code


def determine_hours_time_range(begin, end, tz):
    if begin is None:
        begin = tz.localize(datetime.datetime.now()).date()
    if end is None:
        end = begin

    midnight = datetime.time(0, 0)
    begin = tz.localize(datetime.datetime.combine(begin, midnight))
    end = tz.localize(datetime.datetime.combine(end, midnight))
    end += datetime.timedelta(days=1)

    return begin, end


class ResourceType(ModifiableModel, AutoIdentifiedModel):
    MAIN_TYPES = (
        ('space', _('Space')),
        ('person', _('Person')),
        ('item', _('Item'))
    )
    id = models.CharField(primary_key=True, max_length=100)
    main_type = models.CharField(verbose_name=_('Main type'), max_length=20, choices=MAIN_TYPES)
    name = models.CharField(verbose_name=_('Name'), max_length=200)

    class Meta:
        verbose_name = _("resource type")
        verbose_name_plural = _("resource types")
        ordering = ('name',)

    def __str__(self):
        return "%s (%s)" % (get_translated(self, 'name'), self.id)


class Purpose(ModifiableModel, NameIdentifiedModel):
    id = models.CharField(primary_key=True, max_length=100)
    parent = models.ForeignKey('Purpose', verbose_name=_('Parent'), null=True, blank=True, related_name="children",
                               on_delete=models.SET_NULL)
    name = models.CharField(verbose_name=_('Name'), max_length=200)
    public = models.BooleanField(default=True, verbose_name=_('Public'))

    class Meta:
        verbose_name = _("purpose")
        verbose_name_plural = _("purposes")
        ordering = ('name',)

    def __str__(self):
        return "%s (%s)" % (get_translated(self, 'name'), self.id)


class TermsOfUse(ModifiableModel, AutoIdentifiedModel):
    id = models.CharField(primary_key=True, max_length=100)
    name = models.CharField(verbose_name=_('Name'), max_length=200)
    text = models.TextField(verbose_name=_('Text'))

    class Meta:
        verbose_name = pgettext_lazy('singular', 'terms of use')
        verbose_name_plural = pgettext_lazy('plural', 'terms of use')

    def __str__(self):
        return get_translated_name(self)


class ResourceQuerySet(models.QuerySet):
    def visible_for(self, user):
        if is_general_admin(user):
            return self
        is_in_managed_units = Q(unit__in=Unit.objects.managed_by(user))
        is_public = Q(public=True)
        return self.filter(is_in_managed_units | is_public)

    def modifiable_by(self, user):
        if not is_authenticated_user(user):
            return self.none()

        if is_general_admin(user):
            return self

        units = Unit.objects.managed_by(user)
        return self.filter(unit__in=units)

    def with_perm(self, perm, user):
        units = get_objects_for_user(user, 'unit:%s' % perm, klass=Unit,
                                     with_superuser=False)
        resource_groups = get_objects_for_user(user, 'group:%s' % perm, klass=ResourceGroup,
                                               with_superuser=False)
        return self.filter(Q(unit__in=units) | Q(groups__in=resource_groups)).distinct()


class Resource(ModifiableModel, AutoIdentifiedModel):
    AUTHENTICATION_TYPES = (
        ('none', _('None')),
        ('weak', _('Weak')),
        ('strong', _('Strong'))
    )
    ACCESS_CODE_TYPE_NONE = 'none'
    ACCESS_CODE_TYPE_PIN4 = 'pin4'
    ACCESS_CODE_TYPE_PIN6 = 'pin6'
    ACCESS_CODE_TYPES = (
        (ACCESS_CODE_TYPE_NONE, _('None')),
        (ACCESS_CODE_TYPE_PIN4, _('4-digit PIN code')),
        (ACCESS_CODE_TYPE_PIN6, _('6-digit PIN code')),
    )
    id = models.CharField(primary_key=True, max_length=100)
    public = models.BooleanField(default=True, verbose_name=_('Public'))
    unit = models.ForeignKey('Unit', verbose_name=_('Unit'), db_index=True, null=True, blank=True,
                             related_name="resources", on_delete=models.PROTECT)
    type = models.ForeignKey(ResourceType, verbose_name=_('Resource type'), db_index=True,
                             on_delete=models.PROTECT)
    purposes = models.ManyToManyField(Purpose, verbose_name=_('Purposes'))
    name = models.CharField(verbose_name=_('Name'), max_length=200)
    description = models.TextField(verbose_name=_('Description'), null=True, blank=True)
    need_manual_confirmation = models.BooleanField(verbose_name=_('Need manual confirmation'), default=False)
    authentication = models.CharField(blank=False, verbose_name=_('Authentication'),
                                      max_length=20, choices=AUTHENTICATION_TYPES)
    people_capacity = models.PositiveIntegerField(verbose_name=_('People capacity'), null=True, blank=True)
    area = models.PositiveIntegerField(verbose_name=_('Area (m2)'), null=True, blank=True)

    # if not set, location is inherited from unit
    location = models.PointField(verbose_name=_('Location'), null=True, blank=True, srid=settings.DEFAULT_SRID)

    min_period = models.DurationField(verbose_name=_('Minimum reservation time'),
                                      default=datetime.timedelta(minutes=30))
    max_period = models.DurationField(verbose_name=_('Maximum reservation time'), null=True, blank=True)
    slot_size = models.DurationField(verbose_name=_('Slot size for reservation time'),
                                     default=datetime.timedelta(minutes=30))

    equipment = EquipmentField(Equipment, through='ResourceEquipment', verbose_name=_('Equipment'))
    max_reservations_per_user = models.PositiveIntegerField(verbose_name=_('Maximum number of active reservations per user'),
                                                            null=True, blank=True)
    reservable = models.BooleanField(verbose_name=_('Reservable'), default=False)
    reservation_info = models.TextField(verbose_name=_('Reservation info'), null=True, blank=True)
    responsible_contact_info = models.TextField(verbose_name=_('Responsible contact info'), blank=True)
    generic_terms = models.ForeignKey(TermsOfUse, verbose_name=_('Generic terms'), null=True, blank=True,
                                      on_delete=models.SET_NULL)
    specific_terms = models.TextField(verbose_name=_('Specific terms'), blank=True)
    reservation_requested_notification_extra = models.TextField(verbose_name=_(
        'Extra content to "reservation requested" notification'), blank=True)
    reservation_confirmed_notification_extra = models.TextField(verbose_name=_(
        'Extra content to "reservation confirmed" notification'), blank=True)
    min_price_per_hour = models.DecimalField(verbose_name=_('Min price per hour'), max_digits=8, decimal_places=2,
                                             blank=True, null=True, validators=[MinValueValidator(Decimal('0.00'))])
    max_price_per_hour = models.DecimalField(verbose_name=_('Max price per hour'), max_digits=8, decimal_places=2,
                                             blank=True, null=True, validators=[MinValueValidator(Decimal('0.00'))])

    access_code_type = models.CharField(verbose_name=_('Access code type'), max_length=20, choices=ACCESS_CODE_TYPES,
                                        default=ACCESS_CODE_TYPE_NONE)
    # Access codes can be generated either by the general Respa code or
    # the Kulkunen app. Kulkunen will set the `generate_access_codes`
    # attribute by itself if special access code considerations are
    # needed.
    generate_access_codes = models.BooleanField(
        verbose_name=_('Generate access codes'), default=True, editable=False,
        help_text=_('Should access codes generated by the general system')
    )
    reservable_max_days_in_advance = models.PositiveSmallIntegerField(verbose_name=_('Reservable max. days in advance'),
                                                                      null=True, blank=True)
    reservable_min_days_in_advance = models.PositiveSmallIntegerField(verbose_name=_('Reservable min. days in advance'),
                                                                      null=True, blank=True)
    reservation_metadata_set = models.ForeignKey(
        'resources.ReservationMetadataSet', verbose_name=_('Reservation metadata set'),
        null=True, blank=True, on_delete=models.SET_NULL
    )
    external_reservation_url = models.URLField(
        verbose_name=_('External reservation URL'),
        help_text=_('A link to an external reservation system if this resource is managed elsewhere'),
        null=True, blank=True)

    objects = ResourceQuerySet.as_manager()

    class Meta:
        verbose_name = _("resource")
        verbose_name_plural = _("resources")
        ordering = ('unit', 'name',)

    def __str__(self):
        return "%s (%s)/%s" % (get_translated(self, 'name'), self.id, self.unit)

    @cached_property
    def main_image(self):
        resource_image = next(
            (image for image in self.images.all() if image.type == 'main'),
            None)

        return resource_image.image if resource_image else None

    def validate_reservation_period(self, reservation, user, data=None):
        """
        Check that given reservation if valid for given user.

        Reservation may be provided as Reservation or as a data dict.
        When providing the data dict from a serializer, reservation
        argument must be present to indicate the reservation being edited,
        or None if we are creating a new reservation.
        If the reservation is not valid raises a ValidationError.

        Staff members have no restrictions at least for now.

        Normal users cannot make multi day reservations or reservations
        outside opening hours.

        :type reservation: Reservation
        :type user: User
        :type data: dict[str, Object]
        """

        # no restrictions for staff
        if self.is_admin(user):
            return

        tz = self.unit.get_tz()
        # check if data from serializer is present:
        if data:
            begin = data['begin']
            end = data['end']
        else:
            # if data is not provided, the reservation object has the desired data:
            begin = reservation.begin
            end = reservation.end

        if begin.tzinfo:
            begin = begin.astimezone(tz)
        else:
            begin = tz.localize(begin)
        if end.tzinfo:
            end = end.astimezone(tz)
        else:
            end = tz.localize(end)

        if begin.date() != end.date():
            raise ValidationError(_("You cannot make a multi day reservation"))

        opening_hours = self.get_opening_hours(begin.date(), end.date())
        days = opening_hours.get(begin.date(), None)
        if days is None or not any(day['opens'] and begin >= day['opens'] and end <= day['closes'] for day in days):
            if not self._has_perm(user, 'can_ignore_opening_hours'):
                raise ValidationError(_("You must start and end the reservation during opening hours"))

        if self.max_period and (end - begin) > self.max_period:
            raise ValidationError(_("The maximum reservation length is %(max_period)s") %
                                  {'max_period': humanize_duration(self.max_period)})

    def validate_max_reservations_per_user(self, user):
        """
        Check maximum number of active reservations per user per resource.
        If the user has too many reservations raises ValidationError.

        Staff members have no reservation limits.

        :type user: User
        """
        if self.is_admin(user):
            return

        max_count = self.max_reservations_per_user
        if max_count is not None:
            reservation_count = self.reservations.filter(user=user).active().count()
            if reservation_count >= max_count:
                raise ValidationError(_("Maximum number of active reservations for this resource exceeded."))

    def check_reservation_collision(self, begin, end, reservation):
        overlapping = self.reservations.filter(end__gt=begin, begin__lt=end).active()
        if reservation:
            overlapping = overlapping.exclude(pk=reservation.pk)
        return overlapping.exists()

    def get_available_hours(self, start=None, end=None, duration=None, reservation=None, during_closing=False):
        """
        Returns hours that the resource is not reserved for a given date range

        If include_closed=True, will also return hours when the resource is closed, if it is not reserved.
        This is so that admins can book resources during closing hours. Returns
        the available hours as a list of dicts. The optional reservation argument
        is for disregarding a given reservation during checking, if we wish to
        move an existing reservation. The optional duration argument specifies
        minimum length for periods to be returned.

        :rtype: list[dict[str, datetime.datetime]]
        :type start: datetime.datetime
        :type end: datetime.datetime
        :type duration: datetime.timedelta
        :type reservation: Reservation
        :type during_closing: bool
        """
        today = arrow.get(timezone.now())
        if start is None:
            start = today.floor('day').naive
        if end is None:
            end = today.replace(days=+1).floor('day').naive
        if not start.tzinfo and not end.tzinfo:
            """
            Only try to localize naive dates
            """
            tz = timezone.get_current_timezone()
            start = tz.localize(start)
            end = tz.localize(end)

        if not during_closing:
            """
            Check open hours only
            """
            open_hours = self.get_opening_hours(start, end)
            hours_list = []
            for date, open_during_date in open_hours.items():
                for period in open_during_date:
                    if period['opens']:
                        # if the start or end straddle opening hours
                        opens = period['opens'] if period['opens'] > start else start
                        closes = period['closes'] if period['closes'] < end else end
                        # include_closed to prevent recursion, opening hours need not be rechecked
                        hours_list.extend(self.get_available_hours(start=opens,
                                                                   end=closes,
                                                                   duration=duration,
                                                                   reservation=reservation,
                                                                   during_closing=True))
            return hours_list

        reservations = self.reservations.filter(
            end__gte=start, begin__lte=end).order_by('begin')
        hours_list = [({'starts': start})]
        first_checked = False
        for res in reservations:
            # skip the reservation that is being edited
            if res == reservation:
                continue
            # check if the reservation spans the beginning
            if not first_checked:
                first_checked = True
                if res.begin < start:
                    if res.end > end:
                        return []
                    hours_list[0]['starts'] = res.end
                    # proceed to the next reservation
                    continue
            if duration:
                if res.begin - hours_list[-1]['starts'] < duration:
                    # the free period is too short, discard this period
                    hours_list[-1]['starts'] = res.end
                    continue
            hours_list[-1]['ends'] = timezone.localtime(res.begin)
            # check if the reservation spans the end
            if res.end > end:
                return hours_list
            hours_list.append({'starts': timezone.localtime(res.end)})
        # after the last reservation, we must check if the remaining free period is too short
        if duration:
            if end - hours_list[-1]['starts'] < duration:
                hours_list.pop()
                return hours_list
        # otherwise add the remaining free period
        hours_list[-1]['ends'] = end
        return hours_list

    def get_opening_hours(self, begin=None, end=None, opening_hours_cache=None):
        """
        :rtype : dict[str, datetime.datetime]
        :type begin: datetime.date
        :type end: datetime.date
        """
        tz = pytz.timezone(self.unit.time_zone)
        begin, end = determine_hours_time_range(begin, end, tz)

        if opening_hours_cache is None:
            hours_objs = self.opening_hours.filter(open_between__overlap=(begin, end, '[)'))
        else:
            hours_objs = opening_hours_cache

        opening_hours = dict()
        for h in hours_objs:
            opens = h.open_between.lower.astimezone(tz)
            closes = h.open_between.upper.astimezone(tz)
            date = opens.date()
            hours_item = OrderedDict(opens=opens, closes=closes)
            date_item = opening_hours.setdefault(date, [])
            date_item.append(hours_item)

        # Set the dates when the resource is closed.
        date = begin.date()
        end = end.date()
        while date < end:
            if date not in opening_hours:
                opening_hours[date] = [OrderedDict(opens=None, closes=None)]
            date += datetime.timedelta(days=1)

        return opening_hours

    def update_opening_hours(self):
        hours = self.opening_hours.order_by('open_between')
        existing_hours = {}
        for h in hours:
            assert h.open_between.lower not in existing_hours
            existing_hours[h.open_between.lower] = h.open_between.upper

        unit_periods = list(self.unit.periods.all())
        resource_periods = list(self.periods.all())

        # Periods set for the resource always carry a higher priority. If
        # nothing is defined for the resource for a given day, use the
        # periods configured for the unit.
        for period in unit_periods:
            period.priority = 0
        for period in resource_periods:
            period.priority = 1

        earliest_date = None
        latest_date = None
        all_periods = unit_periods + resource_periods
        for period in all_periods:
            if earliest_date is None or period.start < earliest_date:
                earliest_date = period.start
            if latest_date is None or period.end > latest_date:
                latest_date = period.end

        # Assume we delete everything, but remove items from the delete
        # list if the hours are identical.
        to_delete = existing_hours
        to_add = {}
        if all_periods:
            hours = get_opening_hours(self.unit.time_zone, all_periods,
                                      earliest_date, latest_date)
            for hours_items in hours.values():
                for h in hours_items:
                    if not h['opens'] or not h['closes']:
                        continue
                    if h['opens'] in to_delete and h['closes'] == to_delete[h['opens']]:
                            del to_delete[h['opens']]
                            continue
                    to_add[h['opens']] = h['closes']

        if to_delete:
            ret = ResourceDailyOpeningHours.objects.filter(
                open_between__in=[(opens, closes, '[)') for opens, closes in to_delete.items()],
                resource=self
            ).delete()
            assert ret[0] == len(to_delete)

        add_objs = [
            ResourceDailyOpeningHours(resource=self, open_between=(opens, closes, '[)'))
            for opens, closes in to_add.items()
        ]
        if add_objs:
            ResourceDailyOpeningHours.objects.bulk_create(add_objs)

    def is_admin(self, user):
        """
        Check if the given user is an administrator of this resource.

        :type user: users.models.User
        :rtype: bool
        """
        # UserFilterBackend and ReservationFilterSet in resources.api.reservation assume the same behaviour,
        # so if this is changed those need to be changed as well.
        if not self.unit:
            return is_general_admin(user)
        return self.unit.is_admin(user)

    def is_manager(self, user):
        """
        Check if the given user is a manager of this resource.

        :type user: users.models.User
        :rtype: bool
        """
        if not self.unit:
            return is_general_admin(user)
        return self.unit.is_manager(user)

    def _has_perm(self, user, perm, allow_admin=True):
        if not is_authenticated_user(user):
            return False
        # Admins are almighty.
        if self.is_admin(user) and allow_admin:
            return True
        if hasattr(self, '_permission_checker'):
            checker = self._permission_checker
        else:
            checker = ObjectPermissionChecker(user)

        # Permissions can be given per-unit
        if checker.has_perm('unit:%s' % perm, self.unit):
            return True
        # ... or through Resource Groups
        resource_group_perms = [checker.has_perm('group:%s' % perm, rg) for rg in self.groups.all()]
        return any(resource_group_perms)

    def get_users_with_perm(self, perm):
        users = {u for u in get_users_with_perms(self.unit) if u.has_perm('unit:%s' % perm, self.unit)}
        for rg in self.groups.all():
            users |= {u for u in get_users_with_perms(rg) if u.has_perm('group:%s' % perm, rg)}
        return users

    def can_make_reservations(self, user):
        return self.reservable or self._has_perm(user, 'can_make_reservations')

    def can_modify_reservations(self, user):
        return self._has_perm(user, 'can_modify_reservations')

    def can_ignore_opening_hours(self, user):
        return self._has_perm(user, 'can_ignore_opening_hours')

    def can_view_reservation_extra_fields(self, user):
        return self._has_perm(user, 'can_view_reservation_extra_fields')

    def can_access_reservation_comments(self, user):
        return self._has_perm(user, 'can_access_reservation_comments')

    def can_view_catering_orders(self, user):
        return self._has_perm(user, 'can_view_reservation_catering_orders')

    def can_modify_catering_orders(self, user):
        return self._has_perm(user, 'can_modify_reservation_catering_orders')

    def can_approve_reservations(self, user):
        return self._has_perm(user, 'can_approve_reservation', allow_admin=False)

    def can_view_access_codes(self, user):
        return self._has_perm(user, 'can_view_reservation_access_code')

    def is_access_code_enabled(self):
        return self.access_code_type != Resource.ACCESS_CODE_TYPE_NONE

    def get_reservable_max_days_in_advance(self):
        return self.reservable_max_days_in_advance or self.unit.reservable_max_days_in_advance

    def get_reservable_before(self):
        return create_datetime_days_from_now(self.get_reservable_max_days_in_advance())

    def get_reservable_min_days_in_advance(self):
        return self.reservable_min_days_in_advance or self.unit.reservable_min_days_in_advance

    def get_reservable_after(self):
        return create_datetime_days_from_now(self.get_reservable_min_days_in_advance())

    def get_supported_reservation_extra_field_names(self, cache=None):
        if not self.reservation_metadata_set_id:
            return []
        if cache:
            metadata_set = cache[self.reservation_metadata_set_id]
        else:
            metadata_set = self.reservation_metadata_set
        return [x.field_name for x in metadata_set.supported_fields.all()]

    def get_required_reservation_extra_field_names(self, cache=None):
        if not self.reservation_metadata_set:
            return []
        if cache:
            metadata_set = cache[self.reservation_metadata_set_id]
        else:
            metadata_set = self.reservation_metadata_set
        return [x.field_name for x in metadata_set.required_fields.all()]

    def clean(self):
        if self.min_price_per_hour is not None and self.max_price_per_hour is not None:
            if self.min_price_per_hour > self.max_price_per_hour:
                raise ValidationError(
                    {'min_price_per_hour': _('This value cannot be greater than max price per hour')}
                )
        if self.min_period % self.slot_size != datetime.timedelta(0):
            raise ValidationError({'min_period': _('This value must be a multiple of slot_size')})


class ResourceImage(ModifiableModel):
    TYPES = (
        ('main', _('Main photo')),
        ('ground_plan', _('Ground plan')),
        ('map', _('Map')),
        ('other', _('Other')),
    )
    resource = models.ForeignKey('Resource', verbose_name=_('Resource'), db_index=True,
                                 related_name='images', on_delete=models.CASCADE)
    type = models.CharField(max_length=20, verbose_name=_('Type'), choices=TYPES)
    caption = models.CharField(max_length=100, verbose_name=_('Caption'), null=True, blank=True)
    # FIXME: name images based on resource, type, and sort_order
    image = models.ImageField(verbose_name=_('Image'), upload_to='resource_images')
    image_format = models.CharField(max_length=10)
    cropping = ImageRatioField('image', '800x800', verbose_name=_('Cropping'))
    sort_order = models.PositiveSmallIntegerField(verbose_name=_('Sort order'))

    def save(self, *args, **kwargs):
        self._process_image()
        if self.sort_order is None:
            other_images = self.resource.images.order_by('-sort_order')
            if not other_images:
                self.sort_order = 0
            else:
                self.sort_order = other_images[0].sort_order + 1
        if self.type == "main":
            other_main_images = self.resource.images.filter(type="main")
            if other_main_images.exists():
                # Demote other main images to "other".
                # The other solution would be to raise an error, but that would
                # lead to a more awkward API experience (having to first patch other
                # images for the resource, then fix the last one).
                other_main_images.update(type="other")
        return super(ResourceImage, self).save(*args, **kwargs)

    def full_clean(self, exclude=(), validate_unique=True):
        if "image" not in exclude:
            self._process_image()
        return super(ResourceImage, self).full_clean(exclude, validate_unique)

    def _process_image(self):
        """
        Preprocess the uploaded image file, if required.

        This may transcode the image to a JPEG or PNG if it's not either to begin with.

        :raises InvalidImage: Exception raised if the uploaded file is not valid.
        """
        if not self.image:  # No image set - we can't do this right now
            return

        if self.image_format:  # Assume that if image_format is set, no further processing is required
            return

        try:
            img = Image.open(self.image)
            img.load()
        except Exception as exc:
            raise InvalidImage("Image %s not valid (%s)" % (self.image, exc)) from exc

        if img.format not in ("JPEG", "PNG"):  # Needs transcoding.
            if self.type in ("map", "ground_plan"):
                target_format = "PNG"
                save_kwargs = {}
            else:
                target_format = "JPEG"
                save_kwargs = {"quality": 75, "progressive": True}
            image_bio = BytesIO()
            img.save(image_bio, format=target_format, **save_kwargs)
            self.image = ContentFile(
                image_bio.getvalue(),
                name=os.path.splitext(self.image.name)[0] + ".%s" % target_format.lower()
            )
            self.image_format = target_format
        else:  # All good -- keep the file as-is.
            self.image_format = img.format

    def get_full_url(self):
        base_url = getattr(settings, 'RESPA_IMAGE_BASE_URL', None)
        if not base_url:
            return None
        return base_url.rstrip('/') + reverse('resource-image-view', args=[str(self.id)])

    def __str__(self):
        return "%s image for %s" % (self.get_type_display(), str(self.resource))

    class Meta:
        verbose_name = _('resource image')
        verbose_name_plural = _('resource images')
        unique_together = (('resource', 'sort_order'),)


class ResourceEquipment(ModifiableModel):
    """This model represents equipment instances in resources.

    Contains data and description related to a specific equipment instance.
    Data field can be used to set custom attributes for more flexible and fast filtering.
    """
    resource = models.ForeignKey(Resource, related_name='resource_equipment', on_delete=models.CASCADE)
    equipment = models.ForeignKey(Equipment, related_name='resource_equipment', on_delete=models.CASCADE)
    data = HStoreField(null=True, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = pgettext_lazy('singular', 'resource equipment')
        verbose_name_plural = pgettext_lazy('plural', 'resource equipment')

    def __str__(self):
        return "%s / %s" % (self.equipment, self.resource)


class ResourceGroup(ModifiableModel):
    identifier = models.CharField(verbose_name=_('Identifier'), max_length=100)
    name = models.CharField(verbose_name=_('Name'), max_length=200)
    resources = models.ManyToManyField(Resource, verbose_name=_('Resources'), related_name='groups', blank=True)

    class Meta:
        verbose_name = _('Resource group')
        verbose_name_plural = _('Resource groups')
        permissions = RESOURCE_GROUP_PERMISSIONS
        ordering = ('name',)

    def __str__(self):
        return self.name


class ResourceDailyOpeningHours(models.Model):
    """
    Calculated automatically for each day the resource is open
    """
    resource = models.ForeignKey(
        Resource, related_name='opening_hours', on_delete=models.CASCADE, db_index=True
    )
    open_between = DateTimeRangeField()

    def clean(self):
        super().clean()
        if self.objects.filter(resource=self.resource, open_between__overlaps=self.open_between):
            raise ValidationError(_("Overlapping opening hours"))

    class Meta:
        unique_together = [
            ('resource', 'open_between')
        ]
        indexes = [
            GistIndex(fields=['open_between'])
        ]

    def __str__(self):
        if isinstance(self.open_between, tuple):
            lower = self.open_between[0]
            upper = self.open_between[1]
        else:
            lower = self.open_between.lower
            upper = self.open_between.upper
        return "%s: %s -> %s" % (self.resource, lower, upper)
