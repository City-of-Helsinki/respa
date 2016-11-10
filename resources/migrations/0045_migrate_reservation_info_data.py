# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def migrate_translated_data(apps, schema_editor):
    Resource = apps.get_model('resources', 'Resource')
    for resource in Resource.objects.all():
        data = vars(resource)
        if not data['reservation_info'] and not data['responsible_contact_info']:
            continue
        if not resource.reservation_info_fi:
            resource.reservation_info_fi = data['reservation_info']
        if not resource.responsible_contact_info_fi:
            resource.responsible_contact_info_fi = data['responsible_contact_info']
        resource.save(update_fields=['reservation_info_fi', 'responsible_contact_info'])


def reverse_func(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0044_auto_20161110_1046'),
    ]

    operations = [
        migrations.RunPython(migrate_translated_data, reverse_func),
    ]
