# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0005_auto_20150629_1505'),
    ]

    operations = [
        migrations.AddField(
            model_name='resource',
            name='description_en',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='resource',
            name='description_fi',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='resource',
            name='description_sv',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='resource',
            name='name_en',
            field=models.CharField(null=True, max_length=200),
        ),
        migrations.AddField(
            model_name='resource',
            name='name_fi',
            field=models.CharField(null=True, max_length=200),
        ),
        migrations.AddField(
            model_name='resource',
            name='name_sv',
            field=models.CharField(null=True, max_length=200),
        ),
    ]
