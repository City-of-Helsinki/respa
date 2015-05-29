from django.utils import timezone
from django.db import models
from django.conf import settings


class ModifiableModel(models.Model):
    created_at = models.DateTimeField(default=timezone.now())
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, related_name="%(class)s_created")
    modified_at = models.DateTimeField(default=timezone.now())
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
