import datetime
import os
import re
from decimal import Decimal

import arrow
import django.db.models as dbm
from django.apps import apps
from django.conf import settings
from django.contrib.gis.db import models
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.six import BytesIO
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import pgettext_lazy
from django.contrib.postgres.fields import HStoreField
from image_cropping import ImageRatioField
from PIL import Image
from autoslug import AutoSlugField

from resources.errors import InvalidImage

from .base import AutoIdentifiedModel, NameIdentifiedModel, ModifiableModel
from .utils import create_reservable_before_datetime, get_translated, get_translated_name, humanize_duration
from .equipment import Equipment
from .availability import get_opening_hours


def generate_access_code(access_code_type):
    if access_code_type == Resource.ACCESS_CODE_TYPE_NONE:
        return ''
    elif access_code_type == Resource.ACCESS_CODE_TYPE_PIN6:
        return get_random_string(6, '0123456789')
    else:
        raise NotImplementedError('Don\'t know how to generate an access code of type "%s"' % access_code_type)


def validate_access_code(access_code, access_code_type):
    if access_code_type == Resource.ACCESS_CODE_TYPE_NONE:
        return
    elif access_code_type == Resource.ACCESS_CODE_TYPE_PIN6:
        if not re.match('^[0-9]{6}$', access_code):
            raise ValidationError(dict(access_code=_('Invalid value')))
    else:
        raise NotImplementedError('Don\'t know how to validate an access code of type "%s"' % access_code_type)

    return access_code


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

    def __str__(self):
        return "%s (%s)" % (get_translated(self, 'name'), self.id)


class Purpose(ModifiableModel, NameIdentifiedModel):
    id = models.CharField(primary_key=True, max_length=100)
    parent = models.ForeignKey('Purpose', verbose_name=_('Parent'), null=True, blank=True, related_name="children")
    name = models.CharField(verbose_name=_('Name'), max_length=200)
    public = models.BooleanField(default=True, verbose_name=_('Public'))

    class Meta:
        verbose_name = _("purpose")
        verbose_name_plural = _("purposes")

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


class Resource(ModifiableModel, AutoIdentifiedModel):
    AUTHENTICATION_TYPES = (
        ('none', _('None')),
        ('weak', _('Weak')),
        ('strong', _('Strong'))
    )
    ACCESS_CODE_TYPE_NONE = 'none'
    ACCESS_CODE_TYPE_PIN6 = 'pin6'
    ACCESS_CODE_TYPES = (
        (ACCESS_CODE_TYPE_NONE, _('None')),
        (ACCESS_CODE_TYPE_PIN6, _('6-digit pin code')),
    )
    id = models.CharField(primary_key=True, max_length=100)
    public = models.BooleanField(default=True, verbose_name=_('Public'))
    unit = models.ForeignKey('Unit', verbose_name=_('Unit'), db_index=True, null=True, blank=True,
                             related_name="resources")
    type = models.ForeignKey(ResourceType, verbose_name=_('Resource type'), db_index=True)
    purposes = models.ManyToManyField(Purpose, verbose_name=_('Purposes'))
    name = models.CharField(verbose_name=_('Name'), max_length=200)
    description = models.TextField(verbose_name=_('Description'), null=True, blank=True)
    need_manual_confirmation = models.BooleanField(verbose_name=_('Need manual confirmation'), default=False)
    authentication = models.CharField(blank=False, verbose_name=_('Authentication'),
                                      max_length=20, choices=AUTHENTICATION_TYPES)
    people_capacity = models.IntegerField(verbose_name=_('People capacity'), null=True, blank=True)
    area = models.IntegerField(verbose_name=_('Area'), null=True, blank=True)

    # if not set, location is inherited from unit
    location = models.PointField(verbose_name=_('Location'), null=True, blank=True, srid=settings.DEFAULT_SRID)

    min_period = models.DurationField(verbose_name=_('Minimum reservation time'),
                                      default=datetime.timedelta(minutes=30))
    max_period = models.DurationField(verbose_name=_('Maximum reservation time'), null=True, blank=True)

    slug = AutoSlugField(populate_from=get_translated_name, unique=True)
    equipment = models.ManyToManyField(Equipment, verbose_name=_('Equipment'), through='ResourceEquipment')
    max_reservations_per_user = models.IntegerField(verbose_name=_('Maximum number of active reservations per user'),
                                                    null=True, blank=True)
    reservable = models.BooleanField(verbose_name=_('Reservable'), default=False)
    reservation_info = models.TextField(verbose_name=_('Reservation info'), null=True, blank=True)
    responsible_contact_info = models.TextField(verbose_name=_('Responsible contact info'), blank=True)
    generic_terms = models.ForeignKey(TermsOfUse, verbose_name=_('Generic terms'), null=True, blank=True)
    specific_terms = models.TextField(verbose_name=_('Specific terms'), blank=True)
    reservation_confirmed_notification_extra = models.TextField(verbose_name=_('Extra content to reservation confirmed '
                                                                               'notification'), blank=True)
    min_price_per_hour = models.DecimalField(verbose_name=_('Min price per hour'), max_digits=8, decimal_places=2,
                                             blank=True, null=True, validators=[MinValueValidator(Decimal('0.00'))])
    max_price_per_hour = models.DecimalField(verbose_name=_('Max price per hour'), max_digits=8, decimal_places=2,
                                             blank=True, null=True, validators=[MinValueValidator(Decimal('0.00'))])
    access_code_type = models.CharField(verbose_name=_('Access code type'), max_length=20, choices=ACCESS_CODE_TYPES,
                                        default=ACCESS_CODE_TYPE_NONE)
    reservable_days_in_advance = models.PositiveSmallIntegerField(verbose_name=_('Reservable days in advance'),
                                                                  null=True, blank=True)
    reservation_metadata_set = models.ForeignKey('resources.ReservationMetadataSet', null=True, blank=True)

    class Meta:
        verbose_name = _("resource")
        verbose_name_plural = _("resources")

    def __str__(self):
        return "%s (%s)/%s" % (get_translated(self, 'name'), self.id, self.unit)

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

    def get_opening_hours(self, begin=None, end=None):
        """
        :rtype : dict[str, datetime.datetime]
        :type begin: datetime.date
        :type end: datetime.date
        """
        if self.periods.exists():
            periods = self.periods
        else:
            periods = self.unit.periods

        return get_opening_hours(self.unit.time_zone, periods, begin, end)

    def get_open_from_now(self, dt):
        """
        Returns opening and closing for a given datetime starting from its moment
        and ends on closing time

        If no periods and days that contain given datetime are not found,
        returns none both

        :rtype : dict[str, datetime.datetime]
        :type dt: datetime.datetime
        """

        date, weekday, moment = dt.date(), dt.weekday(), dt.time()

        if self.periods.exists():
            periods = self.periods
        else:
            periods = self.unit.periods

        res = periods.filter(
            start__lte=date, end__gte=date).annotate(
            length=dbm.F('end') - dbm.F('start')
        ).order_by('length').first()

        if res:
            day = res.days.filter(weekday=weekday, opens__lte=moment, closes__gte=moment).first()
            if day:
                closes = dt.combine(dt, day.closes)
                return {'opens': moment, 'closes': closes}

        return {'opens': None, 'closes': None}

    def is_admin(self, user):
        # Currently all staff members are allowed to administrate
        # all resources. Will be more finegrained in the future.
        #
        # UserFilterBackend in resources.api.reservation assumes the same behaviour,
        # so if this is changed that needs to be changed as well.
        return user.is_staff

    def can_make_reservations(self, user):
        return self.is_admin(user) or self.reservable

    def can_approve_reservations(self, user):
        return self.is_admin(user) and user.has_perm('can_approve_reservation', self.unit)

    def is_access_code_enabled(self):
        return self.access_code_type != Resource.ACCESS_CODE_TYPE_NONE

    def can_view_access_codes(self, user):
        return self.is_admin(user) or user.has_perm('can_view_reservation_access_code', self.unit)

    def get_reservable_days_in_advance(self):
        return self.reservable_days_in_advance or self.unit.reservable_days_in_advance

    def get_reservable_before(self):
        return create_reservable_before_datetime(self.get_reservable_days_in_advance())

    def get_supported_reservation_extra_field_names(self):
        if not self.reservation_metadata_set:
            return []
        return self.reservation_metadata_set.supported_fields.values_list('field_name', flat=True)

    def get_required_reservation_extra_field_names(self):
        if not self.reservation_metadata_set:
            return []
        return self.reservation_metadata_set.required_fields.values_list('field_name', flat=True)

    def clean(self):
        if self.min_price_per_hour is not None and self.max_price_per_hour is not None:
            if self.min_price_per_hour > self.max_price_per_hour:
                raise ValidationError(
                    {'min_price_per_hour': _('This value cannot be greater than max price per hour')}
                )


class ResourceImage(ModifiableModel):
    TYPES = (
        ('main', _('Main photo')),
        ('ground_plan', _('Ground plan')),
        ('map', _('Map')),
        ('other', _('Other')),
    )
    resource = models.ForeignKey('Resource', verbose_name=_('Resource'), db_index=True,
                                 related_name='images')
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

    # def get_upload_filename(image, filename): -- used to live here, but was dead code

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
    resource = models.ForeignKey(Resource, related_name='resource_equipment')
    equipment = models.ForeignKey(Equipment, related_name='resource_equipment')
    data = HStoreField(null=True, blank=True)
    description = models.TextField(blank=True)

    objects = models.GeoManager()

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

    def __str__(self):
        return self.name
