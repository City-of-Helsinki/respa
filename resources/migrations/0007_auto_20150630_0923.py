# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0006_auto_20150630_0903'),
    ]

    operations = [
        migrations.AddField(
            model_name='resourcetype',
            name='name_en',
            field=models.CharField(null=True, max_length=200),
        ),
        migrations.AddField(
            model_name='resourcetype',
            name='name_fi',
            field=models.CharField(null=True, max_length=200),
        ),
        migrations.AddField(
            model_name='resourcetype',
            name='name_sv',
            field=models.CharField(null=True, max_length=200),
        ),
    ]
