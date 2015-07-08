# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.postgres.fields.ranges


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0011_auto_20150706_1517'),
    ]

    operations = [
        migrations.AddField(
            model_name='day',
            name='description',
            field=models.CharField(null=True, blank=True, max_length=200, verbose_name='description'),
        ),
        migrations.AddField(
            model_name='day',
            name='length',
            field=django.contrib.postgres.fields.ranges.IntegerRangeField(null=True, blank=True, db_index=True, verbose_name='Range between opens and closes'),
        ),
        migrations.AddField(
            model_name='period',
            name='duration',
            field=django.contrib.postgres.fields.ranges.DateRangeField(null=True, blank=True, db_index=True, verbose_name='Length of period'),
        ),
        migrations.AddField(
            model_name='period',
            name='exception',
            field=models.BooleanField(default=False, verbose_name='Exceptional period'),
        ),
        migrations.AddField(
            model_name='period',
            name='parent',
            field=models.ForeignKey(null=True, blank=True, to='resources.Period', verbose_name='period'),
        ),
        migrations.AddField(
            model_name='reservation',
            name='duration',
            field=django.contrib.postgres.fields.ranges.DateTimeRangeField(null=True, blank=True, db_index=True, verbose_name='Length of reservation'),
        ),
    ]
