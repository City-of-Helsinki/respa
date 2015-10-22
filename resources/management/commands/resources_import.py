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
    option_list = list(BaseCommand.option_list + (
        make_option('--cached', dest='cached', action='store_true', help='cache HTTP requests'),
        make_option('--all', action='store_true', dest='all', help='Import all entities'),
    ))

    importer_types = ['units', 'resources']

    def __init__(self):
        super(Command, self).__init__()
        for imp in self.importer_types:
            opt = make_option('--%s' % imp, dest=imp, action='store_true', help='import %s' % imp)
            self.option_list.append(opt)

    def handle(self, *args, **options):
        if options['cached']:
            requests_cache.install_cache('resources_import')

        importers = get_importers()
        imp_list = ', '.join(sorted(importers.keys()))
        if len(args) != 1:
            raise CommandError("Enter the name of the importer module. Valid importers: %s" % imp_list)
        if not args[0] in importers:
            raise CommandError("Importer %s not found. Valid importers: %s" % (args[0], imp_list))
        imp_class = importers[args[0]]
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
                    method()
