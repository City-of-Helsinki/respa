import datetime
import os

import arrow
import django.db.models as dbm
from django.conf import settings
from django.contrib.gis.db import models
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.utils import timezone
from django.utils.six import BytesIO
from django.utils.translation import ugettext_lazy as _
from image_cropping import ImageRatioField
from PIL import Image
from autoslug import AutoSlugField
from django_hstore import hstore

from resources.errors import InvalidImage

from .base import AutoIdentifiedModel, ModifiableModel
from .utils import get_translated, get_translated_name
from .equipment import Equipment


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


class Purpose(ModifiableModel):
    id = models.CharField(primary_key=True, max_length=100)
    parent = models.ForeignKey('Purpose', verbose_name=_('Parent'), null=True, blank=True, related_name="children")
    name = models.CharField(verbose_name=_('Name'), max_length=200)

    class Meta:
        verbose_name = _("purpose")
        verbose_name_plural = _("purposes")

    def __str__(self):
        return "%s (%s)" % (get_translated(self, 'name'), self.id)


class Resource(ModifiableModel, AutoIdentifiedModel):
    AUTHENTICATION_TYPES = (
        ('none', _('None')),
        ('weak', _('Weak')),
        ('strong', _('Strong'))
    )
    id = models.CharField(primary_key=True, max_length=100)
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

    class Meta:
        verbose_name = _("resource")
        verbose_name_plural = _("resources")

    def __str__(self):
        return "%s (%s)/%s" % (get_translated(self, 'name'), self.id, self.unit)

    def get_reservation_period(self, reservation, data=None):
        """
        Returns accepted start and end times for a suggested reservation.

        Suggested reservation may be provided as Reservation or as a data dict.
        When providing the data dict from a serializer, reservation
        argument must be present to indicate the reservation being edited,
        or None if we are creating a new reservation.
        If the reservation cannot be accepted, raises a ValidationError.

        :rtype : list[datetime.datetime]
        :type reservation: Reservation
        :type data: dict[str, Object]
        """

        # check if data from serializer is present:
        if data:
            begin = data['begin']
            end = data['end']
        else:
            # if data is not provided, the reservation object has the desired data:
            begin = reservation.begin
            end = reservation.end

        days = self.get_opening_hours(begin.date(), end.date())
        if not days.values():
            raise ValidationError(_("No hours for reservation period"))
        for n, day in enumerate(days.values()):
            for m, hours in enumerate(day):
                opening = hours['opens']
                closing = hours['closes']
                try:
                    if end <= begin:
                        raise ValidationError(_("You must end the reservation after it has begun"))
                    if opening is None or begin < opening:
                        raise ValidationError(_("You must start the reservation during opening hours"))
                    if end > closing:
                        raise ValidationError(_("You must end the reservation before closing"))
                    time_since_opening = begin - opening
                    # We round down to the start of the time slot
                    time_slots_since_opening = int(time_since_opening / self.min_period)
                    begin = opening + (time_slots_since_opening * self.min_period)
                    # Duration is calculated modulo time slot
                    duration_in_slots = int((end - begin) / self.min_period)
                    if duration_in_slots <= 0:
                        raise ValidationError(_("The minimum duration for a reservation is " + str(self.min_period)))
                    if self.max_period:
                        if duration_in_slots > self.max_period / self.min_period:
                            raise ValidationError(_("The maximum reservation length is " + str(self.max_period)))
                    duration = duration_in_slots * self.min_period
                    end = begin + duration
                    if not self.is_available(begin, end, reservation):
                        # check that the current reservation is the only overlapping one
                        raise ValidationError(_("The resource is already reserved for some of the period"))
                    return begin, end
                except ValidationError as e:
                    if n + 1 == len(days) and m + 1 == len(day):
                        # Last of days, no valid opening hours are found
                        raise e
                    else:
                        pass  # other day might work better

    def is_available(self, begin, end, reservation=None):
        """
        Returns whether the resource is available between the two datetimes

        Will also return true when the resource is closed, if it is not reserved.
        The optional reservation argument is for disregarding a given
        reservation.

        :rtype : bool
        :type begin: datetime.datetime
        :type end: datetime.datetime
        :type reservation: Reservation
        """
        hours = self.get_available_hours(begin, end, reservation=reservation)
        if hours:
            if begin == hours[0]['starts'] and end == hours[0]['ends']:
                return True
        return False

    def get_available_hours(self, start=None, end=None, duration=None, reservation=None):
        """
        Returns hours that the resource is not reserved for a given date range

        Will also return hours when the resource is closed, if it is not reserved.
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

        today = arrow.get()
        if begin is None:
            begin = today.floor('day').datetime
        if end is None:
            end = begin  # today.replace(days=+1).floor('day').datetime
        from .availability import get_opening_hours
        return get_opening_hours(periods, begin, end)

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
    data = hstore.DictionaryField(null=True, blank=True)
    description = models.TextField(blank=True)

    objects = hstore.HStoreGeoManager()

    class Meta:
        verbose_name = _('resource equipment')
        verbose_name_plural = _('resource equipment')

    def __str__(self):
        return "%s / %s" % (self.equipment, self.resource)
