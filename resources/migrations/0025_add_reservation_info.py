# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0024_auto_20151123_2345'),
    ]

    operations = [
        migrations.AddField(
            model_name='resource',
            name='reservation_info',
            field=models.TextField(verbose_name='Reservation info', null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='resource',
            name='max_reservations_per_user',
            field=models.IntegerField(verbose_name='Maximum number of active reservations per user', null=True, blank=True),
        ),
    ]
