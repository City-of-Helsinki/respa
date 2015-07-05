# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0009_auto_20150705_2114'),
    ]

    operations = [
        migrations.AddField(
            model_name='purpose',
            name='name_en',
            field=models.CharField(null=True, max_length=200, verbose_name='Name'),
        ),
        migrations.AddField(
            model_name='purpose',
            name='name_fi',
            field=models.CharField(null=True, max_length=200, verbose_name='Name'),
        ),
        migrations.AddField(
            model_name='purpose',
            name='name_sv',
            field=models.CharField(null=True, max_length=200, verbose_name='Name'),
        ),
    ]
