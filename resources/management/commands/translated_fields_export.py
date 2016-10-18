# -*- coding: utf-8 -*-
"""
Management command to export translated fields for given models' instances
"""

from optparse import make_option
import io

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.translation import override
from modeltranslation.translator import translator, NotRegistered
from django.apps import apps
import xlsxwriter


def make_excel(data):
    """
    Based on models.utils.generate_reservation_xlsx

    Data is a dict where key is the model's name and value is a list
    with first item the translated field names and second item list of instances
    (or a queryset returning such)

    Each model gets added to its own sheet (tab) in XLS file

    :param data:{model_name: [[translated field names], queryset for model]}
    :return:XLS file as bytes
    """

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output)

    for name, (translated_fields, items) in data.items():

        worksheet = workbook.add_worksheet(name)

        headers = [(field, 50) for field in translated_fields]

        header_format = workbook.add_format({'bold': True})

        for column, header in enumerate(headers):
            worksheet.write(0, column, str(header[0]), header_format)
            worksheet.set_column(column, column, header[1])

        for row, item in enumerate(items, 1):
            for column, field in enumerate(translated_fields):
                worksheet.write(row, column, getattr(item, field) or '')

    workbook.close()
    return output.getvalue()


class Command(BaseCommand):
    args = '<model name>'
    help = "Export translated fields"

    export_models = ['Purpose', 'TermsOfUse', 'Resource']

    def add_arguments(self, parser):
        parser.add_argument('--models', type=str, nargs='*', help="Export given models")
        parser.add_argument('--all', action='store_true', help='Export all models')
        parser.add_argument('--out', type=str, nargs=1, help='Output file name')

    def handle(self, *args, **options):

        # Activate the default language for the duration of the import
        # to make sure translated fields are populated correctly.

        resp = []

        if not options.get('out'):
            raise CommandError("Output file name required")

        if options.get('all') and options.get('models'):
            raise CommandError("Use only all or models options, not both")

        if options.get('all'):
            models = self.export_models
        else:
            models = options.get('models')

        # Validate models
        for model_name in models:
            try:
                apps.get_model('resources', model_name)
            except Exception as e:
                raise CommandError(("Problem finding model '%s': " % model_name) + str(e))

        data = {}

        for model_name in models:
            model = apps.get_model('resources', model_name)
            trans_opts = translator.get_options_for_model(model)
            translated_fields = sorted([tr_field.name for field in trans_opts.fields.values() for tr_field in field])

            data[model_name] = [translated_fields, model.objects.all()]

        output = make_excel(data)

        doc = open(options.get('out')[0], 'bw+')
        try:
            doc.write(output)
        except (IOError, OSError) as e:
            print("Problems with file production", e)
        finally:
            doc.close()
