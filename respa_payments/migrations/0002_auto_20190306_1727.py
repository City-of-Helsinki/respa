# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2019-03-06 15:27
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('respa_payments', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='order',
            name='finished',
        ),
        migrations.RemoveField(
            model_name='order',
            name='order_process_report_seen',
        ),
        migrations.RemoveField(
            model_name='order',
            name='payment_service_order_number',
        ),
        migrations.RemoveField(
            model_name='order',
            name='payment_service_paid',
        ),
        migrations.RemoveField(
            model_name='sku',
            name='date_end',
        ),
        migrations.RemoveField(
            model_name='sku',
            name='date_start',
        ),
        migrations.AddField(
            model_name='order',
            name='order_process_log',
            field=models.TextField(blank=True, null=True, verbose_name='Order process log'),
        ),
        migrations.AddField(
            model_name='order',
            name='payment_service_amount',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Payment service amount'),
        ),
        migrations.AddField(
            model_name='order',
            name='payment_service_currency',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Payment service currency'),
        ),
        migrations.AddField(
            model_name='order',
            name='payment_service_status',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Payment service status'),
        ),
        migrations.AddField(
            model_name='order',
            name='payment_service_success',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='order',
            name='order_process_started',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Order process started'),
        ),
        migrations.AlterField(
            model_name='order',
            name='payment_service_timestamp',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Payment service timestamp'),
        ),
    ]