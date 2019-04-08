
# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.db.models import Q
from resources.models import ResourceType, Unit, UnitIdentifier
from respa_berth.models.berth import Berth, GroundBerthPrice
from respa_berth.models.berth_reservation import BerthReservation
from respa_berth.models.purchase import Purchase
from respa_berth.models.sms_message import SMSMessage


class Command(BaseCommand):
    help = 'Migrate data from old tables to new respa_berth tables. Old tables and data are left intact.'
    BERTH_UNIT_IDENTIFIER = 'berth_reservation'
    BERTH_RESOURCE_MAIN_TYPE = 'berth'

    def handle(self, *args, **options):
        self.set_resource_type_main_type()
        self.create_unit_identifiers()
        self.copy_berths()
        self.copy_groundberthprices()
        self.copy_berthreservations()
        self.copy_purchases()
        self.copy_smsmessages()
        self.reset_sequences()

    def set_resource_type_main_type(self):
        # The ResourceType used in the berths should have a berth related main_type for differentiation of resources
        resource_types = ResourceType.objects.filter(Q(name__icontains='vene') | Q(name__icontains='boat'))
        for r in resource_types:
            r.main_type = self.BERTH_RESOURCE_MAIN_TYPE
            r.save()

    def create_unit_identifiers(self):
        # add a UnitIdentifier for each unit, marking them as berth related units
        for u in Unit.objects.all():
            UnitIdentifier.objects.create(unit=u, namespace=self.BERTH_UNIT_IDENTIFIER, value=u.pk)

    def copy_berths(self):
        self.stdout.write('Copying Berths\n')
        count = 0
        with connection.cursor() as cursor:
            cursor.execute('''
                SELECT * FROM hmlvaraus_berth;
            ''')
            for row in dictfetchall(cursor):
                Berth.objects.create(**row)
                count += 1
                if count % 25 == 0:
                    self.stdout.write('Handled %d' % count)
            self.stdout.write('Finished. Handled %d' % count)

    def copy_groundberthprices(self):
        self.stdout.write('Copying GroundBerthsPrices\n')
        count = 0
        with connection.cursor() as cursor:
            cursor.execute('''
                SELECT * FROM hmlvaraus_groundberthprice;
            ''')
            for row in dictfetchall(cursor):
                GroundBerthPrice.objects.create(**row)
                count += 1
                if count % 25 == 0:
                    self.stdout.write('Handled %d' % count)
            self.stdout.write('Finished. Handled %d' % count)

    def copy_berthreservations(self):
        self.stdout.write('Copying BerthReservations\n')
        count = 0
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('''
                    SELECT * FROM hmlvaraus_hmlreservation;
                ''')
                for row in dictfetchall(cursor):
                    BerthReservation.objects.create(**row)
                    count += 1
                    if count % 25 == 0:
                        self.stdout.write('Handled %d' % count)
                self.stdout.write('Finished. Handled %d' % count)

    def copy_purchases(self):
        self.stdout.write('Copying Purchases\n')
        count = 0
        with connection.cursor() as cursor:
            cursor.execute('''
                SELECT * FROM hmlvaraus_purchase;
            ''')
            for row in dictfetchall(cursor):
                data = row.copy()
                berth_reservation_id = data.pop('hml_reservation_id')
                data['berth_reservation_id'] = berth_reservation_id
                Purchase.objects.create(**data)
                count += 1
                if count % 25 == 0:
                    self.stdout.write('Handled %d' % count)
            self.stdout.write('Finished. Handled %d' % count)

    def copy_smsmessages(self):
        self.stdout.write('Copying SMSMessages\n')
        count = 0
        with connection.cursor() as cursor:
            cursor.execute('''
                SELECT * FROM hmlvaraus_smsmessage;
            ''')
            for row in dictfetchall(cursor):
                data = row.copy()
                berth_reservation_id = data.pop('hml_reservation_id')
                data['berth_reservation_id'] = berth_reservation_id
                SMSMessage.objects.create(**data)
                count += 1
                if count % 25 == 0:
                    self.stdout.write('Handled %d' % count)
            self.stdout.write('Finished. Handled %d' % count)

    def reset_sequences(self):
        # after creating rows and setting their primary keys manually, we must reset the autoincrement sequences in the database
        with connection.cursor() as cursor:
            cursor.execute("SELECT setval('respa_berth_berth_id_seq', (SELECT MAX(id) FROM respa_berth_berth))")
            cursor.execute("SELECT setval('respa_berth_groundberthprice_id_seq', (SELECT MAX(id) FROM respa_berth_groundberthprice))")
            cursor.execute("SELECT setval('respa_berth_berthreservation_id_seq', (SELECT MAX(id) FROM respa_berth_berthreservation))")
            cursor.execute("SELECT setval('respa_berth_purchase_id_seq', (SELECT MAX(id) FROM respa_berth_purchase))")
            cursor.execute("SELECT setval('respa_berth_smsmessage_id_seq', (SELECT MAX(id) FROM respa_berth_smsmessage))")


def dictfetchall(cursor):
    """Return all rows from a cursor as a dict
    From Django documentation.
    """
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
