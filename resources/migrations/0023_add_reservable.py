# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0022_merge'),
    ]

    operations = [
        migrations.AddField(
            model_name='resource',
            name='reservable',
            field=models.BooleanField(default=False, verbose_name='Reservable'),
        ),
    ]
