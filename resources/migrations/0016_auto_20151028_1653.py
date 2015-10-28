# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import autoslug.fields
import resources.models.utils


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0015_auto_20151028_1648'),
    ]

    operations = [
        migrations.AlterField(
            model_name='resource',
            name='slug',
            field=autoslug.fields.AutoSlugField(editable=False, unique=True, populate_from=resources.models.utils.get_translated_name),
        ),
        migrations.AlterField(
            model_name='unit',
            name='slug',
            field=autoslug.fields.AutoSlugField(editable=False, unique=True, populate_from=resources.models.utils.get_translated_name),
        ),
    ]
