# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2017-11-21 13:13
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0063_add_daily_opening_hours'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='resourcegroup',
            options={'ordering': ('name',), 'permissions': [('group:can_approve_reservation', 'Can approve reservation'), ('group:can_make_reservations', 'Can make reservations'), ('group:can_modify_reservations', 'Can modify reservations'), ('group:can_ignore_opening_hours', 'Can make reservations outside opening hours'), ('group:can_view_reservation_access_code', 'Can view reservation access code'), ('group:can_view_reservation_extra_fields', 'Can view reservation extra fields'), ('group:can_access_reservation_comments', 'Can access reservation comments'), ('group:can_view_reservation_catering_orders', 'Can view reservation catering orders'), ('group:can_modify_reservation_catering_orders', 'Can modify reservation catering orders')], 'verbose_name': 'Resource group', 'verbose_name_plural': 'Resource groups'},
        ),
        migrations.AlterModelOptions(
            name='unit',
            options={'ordering': ('name',), 'permissions': [('unit:can_approve_reservation', 'Can approve reservation'), ('unit:can_make_reservations', 'Can make reservations'), ('unit:can_modify_reservations', 'Can modify reservations'), ('unit:can_ignore_opening_hours', 'Can make reservations outside opening hours'), ('unit:can_view_reservation_access_code', 'Can view reservation access code'), ('unit:can_view_reservation_extra_fields', 'Can view reservation extra fields'), ('unit:can_access_reservation_comments', 'Can access reservation comments'), ('unit:can_view_reservation_catering_orders', 'Can view reservation catering orders'), ('unit:can_modify_reservation_catering_orders', 'Can modify reservation catering orders')], 'verbose_name': 'unit', 'verbose_name_plural': 'units'},
        ),
    ]
