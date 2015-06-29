# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0003_auto_20150629_1309'),
    ]

    operations = [
        migrations.AddField(
            model_name='day',
            name='closes',
            field=models.TimeField(null=True, verbose_name='Clock as number, 0000 - 2359', blank=True),
        ),
        migrations.AddField(
            model_name='day',
            name='opens',
            field=models.TimeField(null=True, verbose_name='Clock as number, 0000 - 2359', blank=True),
        ),
    ]
