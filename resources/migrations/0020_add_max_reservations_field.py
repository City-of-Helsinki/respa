# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0019_add_equipment_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='resource',
            name='max_reservations_per_user',
            field=models.IntegerField(null=True, verbose_name='Maximum number of active reservations per user'),
        ),
    ]
