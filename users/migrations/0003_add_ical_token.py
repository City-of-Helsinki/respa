# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_auto_20151211_1223'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='ical_token',
            field=models.SlugField(max_length=16, null=True, verbose_name='iCal token', blank=True, unique=True),
        ),
    ]
