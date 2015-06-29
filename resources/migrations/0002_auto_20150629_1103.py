# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='period',
            name='unit',
            field=models.ForeignKey(null=True, blank=True, related_name='periods', to='resources.Unit'),
        ),
        migrations.AlterField(
            model_name='period',
            name='resource',
            field=models.ForeignKey(null=True, blank=True, related_name='periods', to='resources.Resource'),
        ),
        migrations.AlterField(
            model_name='resource',
            name='unit',
            field=models.ForeignKey(null=True, blank=True, to='resources.Unit'),
        ),
    ]
