# Generated by Django 2.1.7 on 2019-06-28 10:24

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0014_order_one_to_one_reservation'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='order',
            name='payer_address_city',
        ),
        migrations.RemoveField(
            model_name='order',
            name='payer_address_street',
        ),
        migrations.RemoveField(
            model_name='order',
            name='payer_address_zip',
        ),
        migrations.RemoveField(
            model_name='order',
            name='payer_email_address',
        ),
        migrations.RemoveField(
            model_name='order',
            name='payer_first_name',
        ),
        migrations.RemoveField(
            model_name='order',
            name='payer_last_name',
        ),
    ]