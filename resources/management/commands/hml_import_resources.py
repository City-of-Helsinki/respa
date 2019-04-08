# -*- coding: utf-8 -*-
"""
Management command to import Hämeenlinna Resources.
"""

import csv

import datetime
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.translation import override

from resources.models import DurationSlot, Resource, ResourceType, Unit
from resources.models import ReservationMetadataField, ReservationMetadataSet
from resources.models import Day, Period
from respa_payments.models import Sku


class Command(BaseCommand):
    args = 'csv file name'
    help = "Import Hämeenlinna Resources from CSV"

    def add_arguments(self, parser):
        parser.add_argument('csvfile')
        parser.add_argument('--run', action='store_true')

    def handle(self, *args, **options):
        self.run = options['run']
        if not self.run:
            self.stdout.write('Doing a dry run. To actually write data use --run')
        # Activate the default language for the duration of the import
        # to make sure translated fields are populated correctly.
        default_language = settings.LANGUAGES[0][0]
        metadata_set = self.get_or_create_metadata_set()
        resource_type = self.get_or_create_resource_type()

        with open(options['csvfile'], newline='') as csvfile, override(default_language), transaction.atomic():
            # row keys:
            # Kohteen nimi,Resurssin nimi,Varauksen nimi,Varauksen kesto,Hinta (sis alv),Vero%
            csvreader = csv.DictReader(csvfile)
            for row in csvreader:
                try:
                    unit = Unit.objects.get(name_fi=row['Kohteen nimi'])
                    resource_data = {
                        'unit': unit,
                        'name_fi': row['Resurssin nimi'],
                        # 'name_en': row['Resurssin nimi'],
                        # 'name_sv': row['Resurssin nimi'],
                        'need_manual_confirmation': True,
                        'authentication': 'unauthenticated',
                        'use_payments': True,
                        'reservation_metadata_set': metadata_set,
                        'type': resource_type,
                        'reservable': True,
                    }
                    duration_slot_data = {
                        'duration': row['Varauksen kesto'].strip('\n'),
                    }
                    sku_data = {
                        'name': row['Varauksen nimi'],
                        'price': row['Hinta (sis alv)'],
                        'vat': row['Vero%'],
                    }
                    resource = self.update_or_create_resource(resource_data)
                    duration_slot_data['resource'] = resource
                    duration_slot = self.update_or_create_duration_slot(duration_slot_data)
                    sku_data['duration_slot'] = duration_slot
                    self.update_or_create_sku(sku_data)

                except Unit.DoesNotExist:
                    self.stdout.write('\nUNIT NOT FOUND: %s' % row['Kohteen nimi'])
                    continue
        self.stdout.write('Done. CHECK Reservation.reservation_length_type and Reservation.type FOR EVERY RESOURCE!\nThey are not automatically set correctly.\nAlso create Purposes in the database!\n')

    def get_or_create_metadata_set(self):
        try:
            return ReservationMetadataSet.objects.get(name='paytrail')
        except ReservationMetadataSet.DoesNotExist:
            rms = ReservationMetadataSet(name='paytrail')
            if self.run:
                rms.save()
                fields = []
                for field_name in ['reserver_name', 'reserver_phone_number', 'reserver_email_address',
                                   'reserver_address_street', 'reserver_address_zip', 'reserver_address_zip']:
                    field, _created = ReservationMetadataField.objects.get_or_create(field_name=field_name)
                    fields.append(field)
                rms.supported_fields.add(*fields)
                rms.required_fields.add(*fields)
        return rms

    def get_or_create_resource_type(self):
        try:
            return ResourceType.objects.get(name_fi='Mökit ja saunat')
        except ResourceType.DoesNotExist:
            rt = ResourceType(main_type='space', name_fi='Mökit ja saunat')
            if self.run:
                rt.save()
        return rt

    def update_or_create_resource(self, data):
        try:
            instance = Resource.objects.get(name_fi=data['name_fi'], unit=data['unit'])
            for key, val in data.items():
                if getattr(instance, key) != val:
                    self.stdout.write('UPDATING RESOURCE {resource}: {key} = {old_val} -> {new_val}'.format(
                        resource=instance.name_fi,
                        key=key,
                        old_val=getattr(instance, key),
                        new_val=val
                    ))
                    setattr(instance, key, val)
        except Resource.DoesNotExist:
            self.stdout.write('\nCREATING NEW RESOURCE')
            self.stdout.write('* Using data: {}'.format(
                ', '.join(['%s: %s' % (item[0], item[1]) for item in data.items()])
            ))
            instance = Resource(**data)
        if self.run:
            instance.save()
            if not instance.opening_hours.exists():
                self.add_opening_hours(instance)
        return instance

    def add_opening_hours(self, resource):
        """
        Create default opening hours
        """
        today = datetime.date.today()
        way_in_the_future = today + datetime.timedelta(weeks=10*52)
        period = Period.objects.create(
            resource=resource,
            start=today, end=way_in_the_future, name="Oletusaukioloajat")
        for i in range(7):
            Day.objects.create(
                period=period, weekday=i, opens=datetime.time(0, 0),
                closes=datetime.time(23, 59)
            )
        resource.update_opening_hours()

    def update_or_create_duration_slot(self, data):
        try:
            instance = DurationSlot.objects.get(resource=data['resource'], duration=data['duration'])
        except DurationSlot.DoesNotExist:
            self.stdout.write('\nCREATING NEW DurationSlot')
            self.stdout.write('* Using data: {}'.format(
                ', '.join(['%s: %s' % (item[0], item[1]) for item in data.items()])
            ))
            instance = DurationSlot(**data)
        if self.run:
            instance.save()
        return instance

    def update_or_create_sku(self, data):
        try:
            instance = Sku.objects.get(
                duration_slot=data['duration_slot'],
                name=data['name']
            )
            for key, val in data.items():
                if getattr(instance, key) != val:
                    self.stdout.write('UPDATING SKU {instance}: {key} = {old_val} -> {new_val}'.format(
                        instance=instance.name,
                        key=key,
                        old_val=getattr(instance, key),
                        new_val=val
                    ))
                    setattr(instance, key, val)
        except Sku.DoesNotExist:
            self.stdout.write('\nCREATING NEW SKU')
            self.stdout.write('* Using data: {}'.format(
                ', '.join(['%s: %s' % (item[0], item[1]) for item in data.items()])
            ))
            instance = Sku(**data)
        if self.run:
            instance.save()
        return instance
