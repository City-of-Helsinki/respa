# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('resources', '0008_auto_20150701_1758'),
    ]

    operations = [
        migrations.CreateModel(
            name='Purpose',
            fields=[
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Time of creation')),
                ('modified_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Time of modification')),
                ('id', models.CharField(serialize=False, max_length=100, primary_key=True)),
                ('main_type', models.CharField(max_length=40, choices=[('audiovisual_work', 'Audiovisual work'), ('manufacturing', 'Manufacturing'), ('watch_and_listen', 'Watch and listen'), ('meet_and_work', 'Meet and work'), ('games', 'Games'), ('events_and_exhibitions', 'Events and exhibitions')], verbose_name='Main type')),
                ('name', models.CharField(max_length=200, verbose_name='Name')),
                ('created_by', models.ForeignKey(null=True, to=settings.AUTH_USER_MODEL, verbose_name='Created by', blank=True, related_name='purpose_created')),
                ('modified_by', models.ForeignKey(null=True, to=settings.AUTH_USER_MODEL, verbose_name='Modified by', blank=True, related_name='purpose_modified')),
            ],
            options={
                'verbose_name_plural': 'resource types',
                'verbose_name': 'resource type',
            },
        ),
        migrations.AddField(
            model_name='resource',
            name='authentication',
            field=models.CharField(choices=[('none', 'None'), ('weak', 'Weak'), ('strong', 'Strong')], max_length=20, blank=True),
        ),
        migrations.AddField(
            model_name='resource',
            name='purposes',
            field=models.ManyToManyField(to='resources.Purpose'),
        ),
    ]
