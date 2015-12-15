# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0026_resource_public'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reservation',
            name='comments',
            field=models.TextField(verbose_name='Comments', blank=True, null=True),
        ),
    ]
