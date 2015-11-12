# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('resources', '0018_add_resource_equipment'),
    ]

    operations = [
        migrations.CreateModel(
            name='EquipmentCategory',
            fields=[
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Time of creation')),
                ('modified_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Time of modification')),
                ('id', models.CharField(primary_key=True, max_length=100, serialize=False)),
                ('name', models.CharField(max_length=200, verbose_name='Name')),
                ('name_fi', models.CharField(null=True, max_length=200, verbose_name='Name')),
                ('name_en', models.CharField(null=True, max_length=200, verbose_name='Name')),
                ('name_sv', models.CharField(null=True, max_length=200, verbose_name='Name')),
                ('created_by', models.ForeignKey(null=True, to=settings.AUTH_USER_MODEL, related_name='equipmentcategory_created', blank=True, verbose_name='Created by')),
                ('modified_by', models.ForeignKey(null=True, to=settings.AUTH_USER_MODEL, related_name='equipmentcategory_modified', blank=True, verbose_name='Modified by')),
            ],
            options={
                'verbose_name_plural': 'equipment categories',
                'verbose_name': 'equipment category',
            },
        ),
        migrations.AddField(
            model_name='equipment',
            name='category',
            field=models.ForeignKey(related_name='equipment', to='resources.EquipmentCategory', verbose_name='Category'),
        ),
    ]
