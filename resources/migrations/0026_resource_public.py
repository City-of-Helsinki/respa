# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0025_add_reservation_info'),
    ]

    operations = [
        migrations.AddField(
            model_name='resource',
            name='public',
            field=models.BooleanField(default=True, verbose_name='Public'),
        ),
    ]
