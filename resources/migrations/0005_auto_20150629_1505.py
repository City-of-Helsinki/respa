# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.gis.db.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0004_auto_20150629_1309'),
    ]

    operations = [
        migrations.AlterField(
            model_name='resource',
            name='area',
            field=models.IntegerField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='resource',
            name='ground_plan',
            field=models.URLField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='resource',
            name='location',
            field=django.contrib.gis.db.models.fields.PointField(null=True, blank=True, srid=4326),
        ),
        migrations.AlterField(
            model_name='resource',
            name='people_capacity',
            field=models.IntegerField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='resource',
            name='photo',
            field=models.URLField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='resource',
            name='unit',
            field=models.ForeignKey(related_name='resources', blank=True, to='resources.Unit', null=True),
        ),
    ]
