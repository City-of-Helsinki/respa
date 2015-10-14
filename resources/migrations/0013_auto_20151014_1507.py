# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0012_auto_20150708_1443'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='purpose',
            options={'verbose_name': 'purpose', 'verbose_name_plural': 'purposes'},
        ),
        migrations.AlterModelOptions(
            name='unitidentifier',
            options={'verbose_name': 'unit identifier', 'verbose_name_plural': 'unit identifiers'},
        ),
        migrations.AlterField(
            model_name='resource',
            name='authentication',
            field=models.CharField(choices=[('none', 'None'), ('weak', 'Weak'), ('strong', 'Strong')], max_length=20, verbose_name='Authentication'),
        ),
        migrations.AlterField(
            model_name='resource',
            name='purposes',
            field=models.ManyToManyField(to='resources.Purpose', verbose_name='Purposes'),
        ),
    ]
