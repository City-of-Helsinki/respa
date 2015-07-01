# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
import django.contrib.gis.db.models.fields
from django.conf import settings
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0007_auto_20150630_0923'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='day',
            options={'verbose_name': 'day', 'verbose_name_plural': 'days'},
        ),
        migrations.AlterModelOptions(
            name='period',
            options={'verbose_name': 'period', 'verbose_name_plural': 'periods'},
        ),
        migrations.AlterModelOptions(
            name='reservation',
            options={'verbose_name': 'reservation', 'verbose_name_plural': 'reservations'},
        ),
        migrations.AlterModelOptions(
            name='resource',
            options={'verbose_name': 'resource', 'verbose_name_plural': 'resources'},
        ),
        migrations.AlterModelOptions(
            name='resourcetype',
            options={'verbose_name': 'resource type', 'verbose_name_plural': 'resource types'},
        ),
        migrations.AlterModelOptions(
            name='unit',
            options={'verbose_name': 'unit', 'verbose_name_plural': 'units'},
        ),
        migrations.AddField(
            model_name='resource',
            name='max_period',
            field=models.DurationField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='resource',
            name='min_period',
            field=models.DurationField(default=datetime.timedelta(0, 1800)),
        ),
        migrations.AlterField(
            model_name='day',
            name='closed',
            field=models.NullBooleanField(verbose_name='Closed', default=False),
        ),
        migrations.AlterField(
            model_name='day',
            name='closes',
            field=models.TimeField(null=True, verbose_name='Time when closes', blank=True),
        ),
        migrations.AlterField(
            model_name='day',
            name='opens',
            field=models.TimeField(null=True, verbose_name='Time when opens', blank=True),
        ),
        migrations.AlterField(
            model_name='day',
            name='period',
            field=models.ForeignKey(verbose_name='Period', related_name='days', to='resources.Period'),
        ),
        migrations.AlterField(
            model_name='day',
            name='weekday',
            field=models.IntegerField(choices=[(0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday')], verbose_name='Weekday'),
        ),
        migrations.AlterField(
            model_name='period',
            name='closed',
            field=models.BooleanField(verbose_name='Closed', default=False),
        ),
        migrations.AlterField(
            model_name='period',
            name='description',
            field=models.CharField(null=True, verbose_name='Description', max_length=500, blank=True),
        ),
        migrations.AlterField(
            model_name='period',
            name='end',
            field=models.DateField(verbose_name='End date'),
        ),
        migrations.AlterField(
            model_name='period',
            name='name',
            field=models.CharField(verbose_name='Name', max_length=200),
        ),
        migrations.AlterField(
            model_name='period',
            name='resource',
            field=models.ForeignKey(null=True, verbose_name='Resource', blank=True, related_name='periods', to='resources.Resource'),
        ),
        migrations.AlterField(
            model_name='period',
            name='start',
            field=models.DateField(verbose_name='Start date'),
        ),
        migrations.AlterField(
            model_name='period',
            name='unit',
            field=models.ForeignKey(null=True, verbose_name='Unit', blank=True, related_name='periods', to='resources.Unit'),
        ),
        migrations.AlterField(
            model_name='reservation',
            name='begin',
            field=models.DateTimeField(verbose_name='Begin time'),
        ),
        migrations.AlterField(
            model_name='reservation',
            name='created_at',
            field=models.DateTimeField(verbose_name='Time of creation', default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='reservation',
            name='created_by',
            field=models.ForeignKey(null=True, verbose_name='Created by', blank=True, related_name='reservation_created', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='reservation',
            name='end',
            field=models.DateTimeField(verbose_name='End time'),
        ),
        migrations.AlterField(
            model_name='reservation',
            name='modified_at',
            field=models.DateTimeField(verbose_name='Time of modification', default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='reservation',
            name='modified_by',
            field=models.ForeignKey(null=True, verbose_name='Modified by', blank=True, related_name='reservation_modified', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='reservation',
            name='resource',
            field=models.ForeignKey(verbose_name='Resource', related_name='reservations', to='resources.Resource'),
        ),
        migrations.AlterField(
            model_name='reservation',
            name='user',
            field=models.ForeignKey(null=True, verbose_name='User', blank=True, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='resource',
            name='area',
            field=models.IntegerField(null=True, verbose_name='Area', blank=True),
        ),
        migrations.AlterField(
            model_name='resource',
            name='created_at',
            field=models.DateTimeField(verbose_name='Time of creation', default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='resource',
            name='created_by',
            field=models.ForeignKey(null=True, verbose_name='Created by', blank=True, related_name='resource_created', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='resource',
            name='description',
            field=models.TextField(null=True, verbose_name='Description', blank=True),
        ),
        migrations.AlterField(
            model_name='resource',
            name='description_en',
            field=models.TextField(null=True, verbose_name='Description', blank=True),
        ),
        migrations.AlterField(
            model_name='resource',
            name='description_fi',
            field=models.TextField(null=True, verbose_name='Description', blank=True),
        ),
        migrations.AlterField(
            model_name='resource',
            name='description_sv',
            field=models.TextField(null=True, verbose_name='Description', blank=True),
        ),
        migrations.AlterField(
            model_name='resource',
            name='ground_plan',
            field=models.URLField(null=True, verbose_name='Ground plan URL', blank=True),
        ),
        migrations.AlterField(
            model_name='resource',
            name='location',
            field=django.contrib.gis.db.models.fields.PointField(null=True, srid=4326, verbose_name='Location', blank=True),
        ),
        migrations.AlterField(
            model_name='resource',
            name='modified_at',
            field=models.DateTimeField(verbose_name='Time of modification', default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='resource',
            name='modified_by',
            field=models.ForeignKey(null=True, verbose_name='Modified by', blank=True, related_name='resource_modified', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='resource',
            name='name',
            field=models.CharField(verbose_name='Name', max_length=200),
        ),
        migrations.AlterField(
            model_name='resource',
            name='name_en',
            field=models.CharField(null=True, verbose_name='Name', max_length=200),
        ),
        migrations.AlterField(
            model_name='resource',
            name='name_fi',
            field=models.CharField(null=True, verbose_name='Name', max_length=200),
        ),
        migrations.AlterField(
            model_name='resource',
            name='name_sv',
            field=models.CharField(null=True, verbose_name='Name', max_length=200),
        ),
        migrations.AlterField(
            model_name='resource',
            name='need_manual_confirmation',
            field=models.BooleanField(verbose_name='Need manual confirmation', default=False),
        ),
        migrations.AlterField(
            model_name='resource',
            name='people_capacity',
            field=models.IntegerField(null=True, verbose_name='People capacity', blank=True),
        ),
        migrations.AlterField(
            model_name='resource',
            name='photo',
            field=models.URLField(null=True, verbose_name='Photo URL', blank=True),
        ),
        migrations.AlterField(
            model_name='resource',
            name='type',
            field=models.ForeignKey(verbose_name='Resource type', to='resources.ResourceType'),
        ),
        migrations.AlterField(
            model_name='resource',
            name='unit',
            field=models.ForeignKey(null=True, verbose_name='Unit', blank=True, related_name='resources', to='resources.Unit'),
        ),
        migrations.AlterField(
            model_name='resourcetype',
            name='created_at',
            field=models.DateTimeField(verbose_name='Time of creation', default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='resourcetype',
            name='created_by',
            field=models.ForeignKey(null=True, verbose_name='Created by', blank=True, related_name='resourcetype_created', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='resourcetype',
            name='main_type',
            field=models.CharField(choices=[('space', 'Space'), ('person', 'Person'), ('item', 'Item')], verbose_name='Main type', max_length=20),
        ),
        migrations.AlterField(
            model_name='resourcetype',
            name='modified_at',
            field=models.DateTimeField(verbose_name='Time of modification', default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='resourcetype',
            name='modified_by',
            field=models.ForeignKey(null=True, verbose_name='Modified by', blank=True, related_name='resourcetype_modified', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='resourcetype',
            name='name',
            field=models.CharField(verbose_name='Name', max_length=200),
        ),
        migrations.AlterField(
            model_name='resourcetype',
            name='name_en',
            field=models.CharField(null=True, verbose_name='Name', max_length=200),
        ),
        migrations.AlterField(
            model_name='resourcetype',
            name='name_fi',
            field=models.CharField(null=True, verbose_name='Name', max_length=200),
        ),
        migrations.AlterField(
            model_name='resourcetype',
            name='name_sv',
            field=models.CharField(null=True, verbose_name='Name', max_length=200),
        ),
        migrations.AlterField(
            model_name='unit',
            name='address_postal_full',
            field=models.CharField(null=True, verbose_name='Full postal address', max_length=100, blank=True),
        ),
        migrations.AlterField(
            model_name='unit',
            name='address_zip',
            field=models.CharField(null=True, verbose_name='Postal code', max_length=10, blank=True),
        ),
        migrations.AlterField(
            model_name='unit',
            name='created_at',
            field=models.DateTimeField(verbose_name='Time of creation', default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='unit',
            name='created_by',
            field=models.ForeignKey(null=True, verbose_name='Created by', blank=True, related_name='unit_created', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='unit',
            name='description',
            field=models.TextField(null=True, verbose_name='Description', blank=True),
        ),
        migrations.AlterField(
            model_name='unit',
            name='description_en',
            field=models.TextField(null=True, verbose_name='Description', blank=True),
        ),
        migrations.AlterField(
            model_name='unit',
            name='description_fi',
            field=models.TextField(null=True, verbose_name='Description', blank=True),
        ),
        migrations.AlterField(
            model_name='unit',
            name='description_sv',
            field=models.TextField(null=True, verbose_name='Description', blank=True),
        ),
        migrations.AlterField(
            model_name='unit',
            name='email',
            field=models.EmailField(null=True, verbose_name='Email', max_length=100, blank=True),
        ),
        migrations.AlterField(
            model_name='unit',
            name='location',
            field=django.contrib.gis.db.models.fields.PointField(null=True, srid=4326, verbose_name='Location'),
        ),
        migrations.AlterField(
            model_name='unit',
            name='modified_at',
            field=models.DateTimeField(verbose_name='Time of modification', default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='unit',
            name='modified_by',
            field=models.ForeignKey(null=True, verbose_name='Modified by', blank=True, related_name='unit_modified', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='unit',
            name='name',
            field=models.CharField(verbose_name='Name', max_length=200),
        ),
        migrations.AlterField(
            model_name='unit',
            name='name_en',
            field=models.CharField(null=True, verbose_name='Name', max_length=200),
        ),
        migrations.AlterField(
            model_name='unit',
            name='name_fi',
            field=models.CharField(null=True, verbose_name='Name', max_length=200),
        ),
        migrations.AlterField(
            model_name='unit',
            name='name_sv',
            field=models.CharField(null=True, verbose_name='Name', max_length=200),
        ),
        migrations.AlterField(
            model_name='unit',
            name='phone',
            field=models.CharField(null=True, verbose_name='Phone number', max_length=30, blank=True),
        ),
        migrations.AlterField(
            model_name='unit',
            name='picture_caption',
            field=models.CharField(null=True, verbose_name='Picture caption', max_length=200, blank=True),
        ),
        migrations.AlterField(
            model_name='unit',
            name='picture_caption_en',
            field=models.CharField(null=True, verbose_name='Picture caption', max_length=200, blank=True),
        ),
        migrations.AlterField(
            model_name='unit',
            name='picture_caption_fi',
            field=models.CharField(null=True, verbose_name='Picture caption', max_length=200, blank=True),
        ),
        migrations.AlterField(
            model_name='unit',
            name='picture_caption_sv',
            field=models.CharField(null=True, verbose_name='Picture caption', max_length=200, blank=True),
        ),
        migrations.AlterField(
            model_name='unit',
            name='picture_url',
            field=models.URLField(null=True, verbose_name='Picture URL', blank=True),
        ),
        migrations.AlterField(
            model_name='unit',
            name='street_address',
            field=models.CharField(null=True, verbose_name='Street address', max_length=100),
        ),
        migrations.AlterField(
            model_name='unit',
            name='street_address_en',
            field=models.CharField(null=True, verbose_name='Street address', max_length=100),
        ),
        migrations.AlterField(
            model_name='unit',
            name='street_address_fi',
            field=models.CharField(null=True, verbose_name='Street address', max_length=100),
        ),
        migrations.AlterField(
            model_name='unit',
            name='street_address_sv',
            field=models.CharField(null=True, verbose_name='Street address', max_length=100),
        ),
        migrations.AlterField(
            model_name='unit',
            name='www_url',
            field=models.URLField(null=True, verbose_name='WWW link', max_length=400, blank=True),
        ),
        migrations.AlterField(
            model_name='unit',
            name='www_url_en',
            field=models.URLField(null=True, verbose_name='WWW link', max_length=400, blank=True),
        ),
        migrations.AlterField(
            model_name='unit',
            name='www_url_fi',
            field=models.URLField(null=True, verbose_name='WWW link', max_length=400, blank=True),
        ),
        migrations.AlterField(
            model_name='unit',
            name='www_url_sv',
            field=models.URLField(null=True, verbose_name='WWW link', max_length=400, blank=True),
        ),
        migrations.AlterField(
            model_name='unitidentifier',
            name='namespace',
            field=models.CharField(verbose_name='Namespace', max_length=50),
        ),
        migrations.AlterField(
            model_name='unitidentifier',
            name='unit',
            field=models.ForeignKey(verbose_name='Unit', related_name='identifiers', to='resources.Unit'),
        ),
        migrations.AlterField(
            model_name='unitidentifier',
            name='value',
            field=models.CharField(verbose_name='Value', max_length=100),
        ),
    ]
