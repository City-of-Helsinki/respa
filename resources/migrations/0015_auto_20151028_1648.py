# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0014_add_resource_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='resource',
            name='slug',
            field=models.CharField(editable=False, blank=True, max_length=100, default=''),
        ),
        migrations.AddField(
            model_name='unit',
            name='slug',
            field=models.CharField(editable=False, blank=True, max_length=100, default=''),
        ),
    ]
