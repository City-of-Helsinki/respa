# -*- coding: utf-8 -*-

import logging
import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.translation import override
from optparse import make_option

from resources.models import AccessibilityViewpoint, ResourceAccessbility


LOG = logging.getLogger(__name__)
REQUESTS_TIMEOUT = 15


class Command(BaseCommand):
    args = '<module>'
    help = "Import accessibility data"

    def add_arguments(self, parser):
        parser.add_argument('--url', action='store', dest='url', default=settings.RESPA_ACCESSIBILITY_API_BASE_URL,
                            help='Import from a given URL')

    def handle(self, *args, **options):
        url = options['url'].rstrip('/')

        # Activate the default language for the duration of the import
        # to make sure translated fields are populated correctly.
        default_language = settings.LANGUAGES[0][0]

        with override(default_language), transaction.atomic():
            self.fetch_viewpoints(url)
        with override(default_language), transaction.atomic():
            self.fetch_resource_accessibility_data(url)

    def fetch_viewpoints(self, base_url):
        """ Populate accessibility viewpoints from the accessibility API """
        url = '%s/api/v1/accessibility/viewpoints' % base_url
        try:
            response = requests.get(url, timeout=REQUESTS_TIMEOUT)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            LOG.exception('Accessibility data import failed. Problem communicating with Accessibility API.')
            raise e
        except ValueError as e:
            LOG.exception('Accessibility data import failed. Response did not contain JSON')
            raise e

        for viewpoint_data in data:

            vp, created = AccessibilityViewpoint.objects.get_or_create()



