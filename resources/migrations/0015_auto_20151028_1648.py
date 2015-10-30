# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import autoslug.fields
import resources.models.utils
from autoslug.utils import get_prepopulated_value


def backwards(apps, schema_editor):
    pass


def forwards(apps, schema_editor, **kwargs):
    """
    Add slugs to existing Units and Resources.
    """
    force = kwargs.get('force', False)
    Resource = apps.get_model('resources', 'Resource')
    resources = Resource.objects.all() if force else Resource.objects.filter(slug='')
    for resource in resources:
        resource.slug = get_prepopulated_value(resource._meta.get_field('slug'), resource)
        resource.save()
    Unit = apps.get_model('resources', 'Unit')
    units = Unit.objects.all() if force else Unit.objects.filter(slug='')
    for unit in units:
        unit.slug = get_prepopulated_value(unit._meta.get_field('slug'), unit)
        unit.save()


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0014_add_resource_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='resource',
            name='slug',
            field=autoslug.fields.AutoSlugField(editable=False, populate_from=resources.models.utils.get_translated_name, blank=True),
        ),
        migrations.AddField(
            model_name='unit',
            name='slug',
            field=autoslug.fields.AutoSlugField(editable=False, populate_from=resources.models.utils.get_translated_name, blank=True),
        ),
        migrations.RunPython(forwards, backwards),
    ]
