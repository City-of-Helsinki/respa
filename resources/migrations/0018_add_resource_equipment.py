# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone
from django.conf import settings
import django.contrib.postgres.fields.hstore


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('resources', '0017_uneditable_internal_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='Equipment',
            fields=[
                ('created_at', models.DateTimeField(verbose_name='Time of creation', default=django.utils.timezone.now)),
                ('modified_at', models.DateTimeField(verbose_name='Time of modification', default=django.utils.timezone.now)),
                ('id', models.CharField(primary_key=True, max_length=100, serialize=False)),
                ('name', models.CharField(verbose_name='Name', max_length=200)),
                ('name_fi', models.CharField(verbose_name='Name', null=True, max_length=200)),
                ('name_en', models.CharField(verbose_name='Name', null=True, max_length=200)),
                ('name_sv', models.CharField(verbose_name='Name', null=True, max_length=200)),
                ('created_by', models.ForeignKey(blank=True, verbose_name='Created by', to=settings.AUTH_USER_MODEL, related_name='equipment_created', null=True)),
                ('modified_by', models.ForeignKey(blank=True, verbose_name='Modified by', to=settings.AUTH_USER_MODEL, related_name='equipment_modified', null=True)),
            ],
            options={
                'verbose_name': 'equipment',
                'verbose_name_plural': 'equipment',
            },
        ),
        migrations.CreateModel(
            name='EquipmentAlias',
            fields=[
                ('created_at', models.DateTimeField(verbose_name='Time of creation', default=django.utils.timezone.now)),
                ('modified_at', models.DateTimeField(verbose_name='Time of modification', default=django.utils.timezone.now)),
                ('id', models.CharField(primary_key=True, max_length=100, serialize=False)),
                ('name', models.CharField(verbose_name='Name', max_length=200)),
                ('language', models.CharField(choices=[('fi', 'Finnish'), ('en', 'English'), ('sv', 'Swedish')], max_length=3, default='fi')),
                ('created_by', models.ForeignKey(blank=True, verbose_name='Created by', to=settings.AUTH_USER_MODEL, related_name='equipmentalias_created', null=True)),
                ('equipment', models.ForeignKey(related_name='aliases', to='resources.Equipment')),
                ('modified_by', models.ForeignKey(blank=True, verbose_name='Modified by', to=settings.AUTH_USER_MODEL, related_name='equipmentalias_modified', null=True)),
            ],
            options={
                'verbose_name': 'equipment alias',
                'verbose_name_plural': 'equipment aliases',
            },
        ),
        migrations.CreateModel(
            name='ResourceEquipment',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(verbose_name='Time of creation', default=django.utils.timezone.now)),
                ('modified_at', models.DateTimeField(verbose_name='Time of modification', default=django.utils.timezone.now)),
                ('data', django.contrib.postgres.fields.hstore.HStoreField(blank=True, null=True)),
                ('description', models.TextField(blank=True)),
                ('description_fi', models.TextField(blank=True, null=True)),
                ('description_en', models.TextField(blank=True, null=True)),
                ('description_sv', models.TextField(blank=True, null=True)),
                ('created_by', models.ForeignKey(blank=True, verbose_name='Created by', to=settings.AUTH_USER_MODEL, related_name='resourceequipment_created', null=True)),
                ('equipment', models.ForeignKey(related_name='resource_equipment', to='resources.Equipment')),
                ('modified_by', models.ForeignKey(blank=True, verbose_name='Modified by', to=settings.AUTH_USER_MODEL, related_name='resourceequipment_modified', null=True)),
                ('resource', models.ForeignKey(related_name='resource_equipment', to='resources.Resource')),
            ],
            options={
                'verbose_name': 'resource equipment',
                'verbose_name_plural': 'resource equipment',
            },
        ),
        migrations.AddField(
            model_name='resource',
            name='equipment',
            field=models.ManyToManyField(verbose_name='Equipment', through='resources.ResourceEquipment', to='resources.Equipment'),
        ),
    ]
