# -*- coding: utf-8 -*-
from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.translation import override
from modeltranslation.translator import translator, NotRegistered


class Command(BaseCommand):
    args = '<model name>'
    help = "Export translated fields"

    export_models = ['Purpose', 'TermsOfUse', 'Resource']

    def add_arguments(self, parser):
        parser.add_argument('--models', type=str, nargs='*', help="Export given models")
        parser.add_argument('--all', action='store_true', help='Export all models')

    def handle(self, *args, **options):
        pass
