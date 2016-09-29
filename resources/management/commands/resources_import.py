# -*- coding: utf-8 -*-
from optparse import make_option

import requests_cache
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.translation import override

from resources.importer.base import get_importers


class Command(BaseCommand):
    args = '<module>'
    help = "Import resources data"

    importer_types = ['units', 'resources']

    def add_arguments(self, parser):
        parser.add_argument('module', type=str)

        parser.add_argument('--cached', dest='cached', action='store_true', help='cache HTTP requests')
        parser.add_argument('--all', action='store_true', dest='all', help='Import all entities')
        parser.add_argument('--url', action='store', dest='url', help='Import from a given URL')
        for imp in self.importer_types:
            parser.add_argument('--%s' % imp, dest=imp, action='store_true', help='import %s' % imp)

    def handle(self, *args, **options):
        if options['cached']:
            requests_cache.install_cache('resources_import')

        importers = get_importers()
        imp_list = ', '.join(sorted(importers.keys()))
        imp_name = options.get('module')
        if not imp_name:
            raise CommandError("Enter the name of the importer module. Valid importers: %s" % imp_list)
        if imp_name not in importers:
            raise CommandError("Importer %s not found. Valid importers: %s" % (args[0], imp_list))
        imp_class = importers[imp_name]
        importer = imp_class(options)

        # Activate the default language for the duration of the import
        # to make sure translated fields are populated correctly.
        default_language = settings.LANGUAGES[0][0]
        for imp_type in self.importer_types:
            name = "import_%s" % imp_type
            method = getattr(importer, name, None)
            if options[imp_type]:
                if not method:
                    raise CommandError("Importer %s does not support importing %s" % (name, imp_type))
            else:
                if not options['all']:
                    continue

            if method:
                with override(default_language), transaction.atomic():
                    kwargs = {}
                    url = options.pop('url', None)
                    if url:
                        kwargs['url'] = url
                    method(**kwargs)
