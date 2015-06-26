# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.gis.db.models.fields
from django.conf import settings
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Day',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('weekday', models.IntegerField(choices=[(0, 'maanantai'), (1, 'tiistai'), (2, 'keskiviikko'), (3, 'torstai'), (4, 'perjantai'), (5, 'lauantai'), (6, 'sunnuntai')], verbose_name='Day of week as a number 1-7')),
                ('opens', models.IntegerField(verbose_name='Clock as number, 0000 - 2359')),
                ('closes', models.IntegerField(verbose_name='Clock as number, 0000 - 2359')),
                ('closed', models.NullBooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Period',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('start', models.DateField()),
                ('end', models.DateField()),
                ('name', models.CharField(max_length=200)),
                ('description', models.CharField(max_length=500, null=True)),
                ('closed', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Reservation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('modified_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('begin', models.DateTimeField()),
                ('end', models.DateTimeField()),
                ('created_by', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='reservation_created', null=True)),
                ('modified_by', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='reservation_modified', null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Resource',
            fields=[
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('modified_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('id', models.CharField(max_length=100, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True, null=True)),
                ('photo', models.URLField(null=True)),
                ('need_manual_confirmation', models.BooleanField(default=False)),
                ('people_capacity', models.IntegerField(null=True)),
                ('area', models.IntegerField(null=True)),
                ('ground_plan', models.URLField(null=True)),
                ('location', django.contrib.gis.db.models.fields.PointField(srid=4326, null=True)),
                ('created_by', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='resource_created', null=True)),
                ('modified_by', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='resource_modified', null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='ResourceType',
            fields=[
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('modified_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('id', models.CharField(max_length=100, primary_key=True, serialize=False)),
                ('main_type', models.CharField(max_length=20, choices=[('space', 'Space'), ('person', 'Person'), ('item', 'Item')])),
                ('name', models.CharField(max_length=200)),
                ('created_by', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='resourcetype_created', null=True)),
                ('modified_by', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='resourcetype_modified', null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Unit',
            fields=[
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('modified_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('id', models.CharField(max_length=50, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200)),
                ('name_fi', models.CharField(max_length=200, null=True)),
                ('name_en', models.CharField(max_length=200, null=True)),
                ('name_sv', models.CharField(max_length=200, null=True)),
                ('description', models.TextField(null=True)),
                ('description_fi', models.TextField(null=True)),
                ('description_en', models.TextField(null=True)),
                ('description_sv', models.TextField(null=True)),
                ('location', django.contrib.gis.db.models.fields.PointField(srid=4326, null=True)),
                ('street_address', models.CharField(max_length=100, null=True)),
                ('street_address_fi', models.CharField(max_length=100, null=True)),
                ('street_address_en', models.CharField(max_length=100, null=True)),
                ('street_address_sv', models.CharField(max_length=100, null=True)),
                ('address_zip', models.CharField(max_length=10, null=True)),
                ('phone', models.CharField(max_length=30, null=True)),
                ('email', models.EmailField(max_length=100, null=True)),
                ('www_url', models.URLField(max_length=400, null=True)),
                ('www_url_fi', models.URLField(max_length=400, null=True)),
                ('www_url_en', models.URLField(max_length=400, null=True)),
                ('www_url_sv', models.URLField(max_length=400, null=True)),
                ('address_postal_full', models.CharField(max_length=100, null=True)),
                ('picture_url', models.URLField(null=True)),
                ('picture_caption', models.CharField(max_length=200, null=True)),
                ('picture_caption_fi', models.CharField(max_length=200, null=True)),
                ('picture_caption_en', models.CharField(max_length=200, null=True)),
                ('picture_caption_sv', models.CharField(max_length=200, null=True)),
                ('created_by', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='unit_created', null=True)),
                ('modified_by', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='unit_modified', null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='UnitIdentifier',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('namespace', models.CharField(max_length=50)),
                ('value', models.CharField(max_length=100)),
                ('unit', models.ForeignKey(to='resources.Unit', related_name='identifiers')),
            ],
        ),
        migrations.AddField(
            model_name='resource',
            name='type',
            field=models.ForeignKey(to='resources.ResourceType'),
        ),
        migrations.AddField(
            model_name='resource',
            name='unit',
            field=models.ForeignKey(to='resources.Unit', null=True),
        ),
        migrations.AddField(
            model_name='reservation',
            name='resource',
            field=models.ForeignKey(to='resources.Resource', related_name='reservations'),
        ),
        migrations.AddField(
            model_name='reservation',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL, null=True),
        ),
        migrations.AddField(
            model_name='period',
            name='resource',
            field=models.ForeignKey(to='resources.Resource', related_name='periods'),
        ),
        migrations.AddField(
            model_name='day',
            name='period',
            field=models.ForeignKey(to='resources.Period', related_name='days'),
        ),
        migrations.AlterUniqueTogether(
            name='unitidentifier',
            unique_together=set([('namespace', 'value'), ('namespace', 'unit')]),
        ),
    ]
