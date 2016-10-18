# -*- coding: utf-8 -*-
from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.translation import override
from modeltranslation.translator import translator, NotRegistered
from django.apps import apps


class Command(BaseCommand):
    args = '<model name>'
    help = "Export translated fields"

    export_models = ['Purpose', 'TermsOfUse', 'Resource']

    def add_arguments(self, parser):
        parser.add_argument('--models', type=str, nargs='*', help="Export given models")
        parser.add_argument('--all', action='store_true', help='Export all models')

    def handle(self, *args, **options):

        # Activate the default language for the duration of the import
        # to make sure translated fields are populated correctly.

        resp = []

        if options.get('all'):
            models = self.export_models
        else:
            models = options.get('models')

        for model_name in models:
            model = apps.get_model('resources', model_name)
            trans_opts = translator.get_options_for_model(model)
            translated_fields = sorted([tr_field.name for field in trans_opts.fields.values() for tr_field in field])

            resp.append(['id'] + translated_fields)

            for obj in model.objects.all():
                resp.append([obj.pk] + [getattr(obj, field) or '' for field in translated_fields])

        print('\n'.join([';'.join(i) for i in resp]))
