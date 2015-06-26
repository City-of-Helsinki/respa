from django.utils import timezone
from django.contrib.gis.db import models
from django.conf import settings
from django.utils.translation import ugettext as _

DEFAULT_LANG = settings.LANGUAGES[0][0]


def get_translated(obj, attr):
    key = "%s_%s" % (attr, DEFAULT_LANG)
    val = getattr(obj, key, None)
    if not val:
        val = getattr(obj, attr)
    return val


class ModifiableModel(models.Model):
    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, related_name="%(class)s_created")
    modified_at = models.DateTimeField(default=timezone.now)
    modified_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, related_name="%(class)s_modified")

    class Meta:
        abstract = True


class Unit(ModifiableModel):
    id = models.CharField(primary_key=True, max_length=50)
    name = models.CharField(max_length=200)
    description = models.TextField(null=True)

    location = models.PointField(null=True, srid=settings.DEFAULT_SRID)
    # organization = models.ForeignKey(...)
    street_address = models.CharField(max_length=100, null=True)
    address_zip = models.CharField(max_length=10, null=True)
    phone = models.CharField(max_length=30, null=True)
    email = models.EmailField(max_length=100, null=True)
    www_url = models.URLField(max_length=400, null=True)
    address_postal_full = models.CharField(max_length=100, null=True)

    picture_url = models.URLField(max_length=200, null=True)
    picture_caption = models.CharField(max_length=200, null=True)

    def __str__(self):
        return "%s (%s)" % (get_translated(self, 'name'), self.id)


class UnitIdentifier(models.Model):
    unit = models.ForeignKey(Unit, db_index=True, related_name='identifiers')
    namespace = models.CharField(max_length=50)
    value = models.CharField(max_length=100)

    class Meta:
        unique_together = (('namespace', 'value'), ('namespace', 'unit'))


class ResourceType(ModifiableModel):
    MAIN_TYPES = (
        ('space', _('Space')),
        ('person', _('Person')),
        ('item', _('Item'))
    )
    id = models.CharField(primary_key=True, max_length=100)
    main_type = models.CharField(max_length=20, choices=MAIN_TYPES)
    name = models.CharField(max_length=200)


class Resource(ModifiableModel):
    id = models.CharField(primary_key=True, max_length=100)
    unit = models.ForeignKey(Unit, db_index=True, null=True)
    type = models.ForeignKey(ResourceType, db_index=True)
    name = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    photo = models.URLField(null=True)
    need_manual_confirmation = models.BooleanField(default=False)

    people_capacity = models.IntegerField(null=True)
    area = models.IntegerField(null=True)
    ground_plan = models.URLField(null=True)

    # if not set, location is inherited from unit
    location = models.PointField(null=True, srid=settings.DEFAULT_SRID)


class Reservation(ModifiableModel):
    resource = models.ForeignKey(Resource, db_index=True, related_name='reservations')
    begin = models.DateTimeField()
    end = models.DateTimeField()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, db_index=True)


STATE_BOOLS = {True: _('open'), False: _('closed')}


class Period(models.Model):
    """
    A period of time to express state of open or closed
    Days that specifies the actual activity hours link here
    """
    resource = models.ForeignKey(Resource, db_index=True, related_name='periods')
    start = models.DateField()
    end = models.DateField()
    name = models.CharField(max_length=200)
    description = models.CharField(null=True, max_length=500)
    closed = models.BooleanField(default=False)

    def __str__(self):
        # FIXME: output date in locale-specific format
        return "{0}, {3}: {1:%d.%m.%Y} - {2:%d.%m.%Y}".format(self.name, self.start, self.end, STATE_BOOLS[self.closed])


class Day(models.Model):
    """
    Day of week and its active start and end time and whether it is open or closed

    Kirjastot.fi API uses closed for both days and periods, don't know which takes precedence
    """
    DAYS_OF_WEEK = (
        (0, _('Monday')),
        (1, _('Tuesday')),
        (2, _('Wednesday')),
        (3, _('Thursday')),
        (4, _('Friday')),
        (5, _('Saturday')),
        (6, _('Sunday'))
    )

    period = models.ForeignKey(Period, db_index=True, related_name='days')
    weekday = models.IntegerField("Day of week as a number 1-7", choices=DAYS_OF_WEEK)
    opens = models.IntegerField("Clock as number, 0000 - 2359")
    closes = models.IntegerField("Clock as number, 0000 - 2359")
    closed = models.NullBooleanField(default=False)  # NOTE: If this is true and the period is false, what then?

    def __str__(self):
        # FIXME: output date in locale-specific format
        return "{4}, {3}: {1:%d.%m.%Y} - {2:%d.%m.%Y}, {0}: {3}".format(
            self.get_weekday_display(), self.period.start, self.period.end, STATE_BOOLS[self.closed], self.period.name)
