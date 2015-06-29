# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0002_auto_20150629_1103'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='day',
            name='closes',
        ),
        migrations.RemoveField(
            model_name='day',
            name='opens',
        ),
    ]
