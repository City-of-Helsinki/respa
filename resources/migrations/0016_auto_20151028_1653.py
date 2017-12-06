# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import resources.models.utils


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0015_auto_20151028_1648'),
    ]

    operations = [
        migrations.AlterField(
            model_name='resource',
            name='slug',
            field=models.CharField(editable=False, blank=True, max_length=100, default=''),
        ),
        migrations.AlterField(
            model_name='unit',
            name='slug',
            field=models.CharField(editable=False, blank=True, max_length=100, default=''),
        ),
    ]
