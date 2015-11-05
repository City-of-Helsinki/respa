# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0016_auto_20151028_1653'),
    ]

    operations = [
        migrations.AlterField(
            model_name='period',
            name='closed',
            field=models.BooleanField(verbose_name='Closed', default=False, editable=False),
        ),
        migrations.AlterField(
            model_name='period',
            name='parent',
            field=models.ForeignKey(to='resources.Period', verbose_name='exception parent period', editable=False, null=True, blank=True),
        ),
    ]
