from django.utils import timezone
from django.db import models
from django.conf import settings

class ModifiableModel(models.Model):
    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, related_name="%(class)s_created")
    modified_at = models.DateTimeField(default=timezone.now)
    modified_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, related_name="%(class)s_modified")

    class Meta:
        abstract = True


class ResourceType(ModifiableModel):
    id = models.CharField(primary_key=True, max_length=100)
    name = models.CharField(max_length=200)
    is_space = models.BooleanField(default=False)


class Resource(ModifiableModel):
    id = models.CharField(primary_key=True, max_length=100)
    type = models.ForeignKey(ResourceType, db_index=True)
    name = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    photo = models.URLField(null=True)
    need_manual_confirmation = models.BooleanField(default=False)

    people_capacity = models.IntegerField(null=True)
    area = models.IntegerField(null=True)
    ground_plan = models.URLField(null=True)


class Reservation(ModifiableModel):
    resource = models.ForeignKey(Resource, db_index=True, related_name='reservations')
    begin = models.DateTimeField()
    end = models.DateTimeField()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, db_index=True)


class Period(models.Model):
    """
    A period of time to express state of open or closed
    Days that specifies the actual activity hours link here
    """
    resource = models.ForeignKey(Resource, db_index=True, related_name='periods')
    start = models.DateField()
    end = models.DateField()
    name = models.CharField(max_length=200)
    closed = models.BooleanField(default=False)

DAYS_OF_WEEK = [
    (1, 'maanantai'),
    (2, 'tiistai'),
    (3, 'keskiviikko'),
    (4, 'torstai'),
    (5, 'perjantai'),
    (6, 'lauantai'),
    (7, 'sunnuntai')]

class Day(models.Model):
    """
    Day of week and its active start and end time and whether it is open or closed

    Kirjastot.fi API uses closed for both days and periods, don't know which takes precedence
    """
    period = models.ForeignKey(Period, db_index=True, related_name='days')
    weekday = models.IntegerField("Day of week as a number 1-7", choices=DAYS_OF_WEEK)
    opens = models.IntegerField("Clock as number, 0000 - 2359")
    closes = models.IntegerField("Clock as number, 0000 - 2359")
    closed = models.NullBooleanField(default=False)  # NOTE: If this is true and the period is false, what then?


