# -*- coding: utf-8 -*-
"""
Management command to import Hämeenlinna Units.
"""

import csv

from django.conf import settings
from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.translation import override

from resources.models import Unit


class Command(BaseCommand):
    args = 'csv file name'
    help = "Import Hämeenlinna Units from CSV"

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
        with open(options['csvfile'], newline='') as csvfile, override(default_language):
            # row keys:
            # Nimi fi, Nimi en, Nimi sv, Kuvaus fi, Kuvaus en, Osoite, Postinumero, Sähköposti (yhteyshenkilön), Puhelinnumero (yhteyshenkilön), Sijainti (koordinaatit, latitude longitude), Kuvan URL
            csvreader = csv.DictReader(csvfile)
            for row in csvreader:
                data = {
                    'name_fi': row['Nimi fi'],
                    'name_en': row['Nimi en'],
                    'name_sv': row['Nimi sv'],
                    'description_fi': row['Kuvaus fi'],
                    # 'description_en': row['Kuvaus en'],
                    'street_address': row['Osoite'],
                    'address_zip': row['Postinumero'],
                    'manager_email': row['Sähköposti (yhteyshenkilön)'],
                    'phone': row['Puhelinnumero (yhteyshenkilön)'],
                    'location': self.create_point(row['Sijainti (koordinaatit, latitude longitude)']),
                    'picture_url': row['Kuvan URL'],
                }
                try:
                    instance = Unit.objects.get(name_fi=data['name_fi'])
                    self.stdout.write('\nFOUND EXISTING UNIT %s' % instance.name_fi)
                    self.update(instance, data)
                except Unit.DoesNotExist:
                    self.stdout.write('\nCREATING NEW UNIT %s' % data['name_fi'])
                    self.create(data)

    def create_point(self, geo_string):
        x, y = geo_string.split(', ')
        return Point(x=float(x), y=float(y), srid=settings.DEFAULT_SRID)

    def create(self, data):
        self.stdout.write('* Using data: {}'.format(
            ', '.join(['%s: %s' % (item[0], item[1]) for item in data.items()])
        ))
        unit = Unit(**data)
        if self.run:
            unit.save()

    def update(self, instance, data):
        for key, val in data.items():
            if getattr(instance, key) != val:
                self.stdout.write('* Updating %s -> %s' % (getattr(instance, key), val))
                setattr(instance, key, val)
        if self.run:
            instance.save()

