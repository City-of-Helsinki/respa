
# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from celery import Celery
from celery.schedules import crontab
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'respa.settings')
app = Celery('respa')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


app.conf.beat_schedule = {
    'retry_sms': {
        'task': 'respa_berth.tasks.retry_sms',
        'schedule': crontab(minute=0, hour='12,14,16')
    },
    'cancel_failed_reservations': {
        'task': 'respa_berth.tasks.cancel_failed_reservations',
        'schedule': crontab(minute=0, hour='12')
    },
    'check_and_handle_reservation_renewals': {
        'task': 'respa_berth.tasks.check_and_handle_reservation_renewals',
        'schedule': crontab(minute=0, hour='13')
    },
    'check_ended_reservations': {
        'task': 'respa_berth.tasks.check_ended_reservations',
        'schedule': crontab(minute=0, hour='14')
    },
    'check_key_returned': {
        'task': 'respa_berth.tasks.check_key_returned',
        'schedule': crontab(minute=0, hour='15')
    },
    'check_reservability': {
        'task': 'respa_berth.tasks.check_reservability',
        'schedule': crontab(minute=0, hour='*/1')
    },
    'clear_unpaid_reservations': {
        'task': 'respa_payments.tasks.clear_unpaid_reservations',
        'schedule': crontab(minute='*')
    },
}
