# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0010_auto_20150705_2151'),
    ]

    operations = [
        migrations.AlterField(
            model_name='resource',
            name='authentication',
            field=models.CharField(choices=[('none', 'None'), ('weak', 'Weak'), ('strong', 'Strong')], max_length=20),
        ),
        migrations.AlterField(
            model_name='resource',
            name='max_period',
            field=models.DurationField(null=True, verbose_name='Maximum reservation time', blank=True),
        ),
        migrations.AlterField(
            model_name='resource',
            name='min_period',
            field=models.DurationField(verbose_name='Minimum reservation time', default=datetime.timedelta(0, 1800)),
        ),
    ]
