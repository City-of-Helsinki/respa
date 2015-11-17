# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0019_add_equipment_category'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='purpose',
            name='main_type',
        ),
        migrations.AddField(
            model_name='purpose',
            name='parent',
            field=models.ForeignKey(to='resources.Purpose', null=True, blank=True, verbose_name='Parent', related_name='children'),
        ),
    ]
