# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import image_cropping.fields
from django.conf import settings
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('resources', '0013_auto_20151014_1507'),
    ]

    operations = [
        migrations.CreateModel(
            name='ResourceImage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, verbose_name='ID', serialize=False)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Time of creation')),
                ('modified_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Time of modification')),
                ('type', models.CharField(choices=[('main', 'Main photo'), ('ground_plan', 'Ground plan'), ('map', 'Map'), ('other', 'Other')], max_length=20, verbose_name='Type')),
                ('caption', models.CharField(max_length=100, blank=True, verbose_name='Caption', null=True)),
                ('caption_fi', models.CharField(max_length=100, blank=True, verbose_name='Caption', null=True)),
                ('caption_en', models.CharField(max_length=100, blank=True, verbose_name='Caption', null=True)),
                ('caption_sv', models.CharField(max_length=100, blank=True, verbose_name='Caption', null=True)),
                ('image', models.ImageField(upload_to='resource_images', verbose_name='Image')),
                ('image_format', models.CharField(max_length=10)),
                ('cropping', image_cropping.fields.ImageRatioField('image', '800x800', help_text=None, adapt_rotation=False, free_crop=False, allow_fullsize=False, hide_image_field=False, verbose_name='Cropping', size_warning=False)),
                ('sort_order', models.PositiveSmallIntegerField(verbose_name='Sort order')),
                ('created_by', models.ForeignKey(to=settings.AUTH_USER_MODEL, blank=True, related_name='resourceimage_created', verbose_name='Created by', null=True)),
                ('modified_by', models.ForeignKey(to=settings.AUTH_USER_MODEL, blank=True, related_name='resourceimage_modified', verbose_name='Modified by', null=True)),
            ],
            options={
                'verbose_name': 'resource image',
                'verbose_name_plural': 'resource images',
            },
        ),
        migrations.RemoveField(
            model_name='resource',
            name='ground_plan',
        ),
        migrations.RemoveField(
            model_name='resource',
            name='photo',
        ),
        migrations.AddField(
            model_name='resourceimage',
            name='resource',
            field=models.ForeignKey(to='resources.Resource', related_name='images', verbose_name='Resource'),
        ),
        migrations.AlterUniqueTogether(
            name='resourceimage',
            unique_together=set([('resource', 'sort_order')]),
        ),
    ]
