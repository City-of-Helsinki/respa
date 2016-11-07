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
from resources.models.utils import make_translation_excel


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
        elif options.get('models'):
            models = options.get('models')
        else:
            raise CommandError("Please give option --all or specific models with --models")

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

        output = io.BytesIO()
        result = make_translation_excel(output, data)

        if not result:
            raise CommandError("Something went wrong with producing Excel")

        doc = open(options.get('out')[0], 'bw+')
        try:
            doc.write(output.getvalue())
        except (IOError, OSError) as e:
            print("Problems with file production", e)
        finally:
            doc.close()
