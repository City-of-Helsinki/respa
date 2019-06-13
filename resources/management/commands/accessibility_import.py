# -*- coding: utf-8 -*-

import logging
import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.translation import override

from resources.models import (
    AccessibilityValue, AccessibilityViewpoint, Resource, ResourceAccessibility,
    UnitAccessibility, UnitIdentifier
)


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
        default_language = settings.LANGUAGE_CODE

        with override(default_language), transaction.atomic():
            self.fetch_viewpoints(url)
        with override(default_language), transaction.atomic():
            self.fetch_resource_accessibility_data(url)
        with override(default_language), transaction.atomic():
            self.fetch_unit_accessibility_data(url)
        self.stdout.write('Finished.')

    def fetch_viewpoints(self, base_url):
        """ Populate accessibility viewpoints from the accessibility API """
        url = '{}/api/v1/accessibility/viewpoints'.format(base_url)
        data = self.make_request(url)
        vp_ids = []

        for viewpoint_data in data:
            vp_id = viewpoint_data['viewpointId']
            if vp_id == 0:
                # id 0 seems to be the "empty" option in a dropdown: "Choose accessibility perspective"
                continue
            vp_ids.append(vp_id)
            vp_attributes = {
                'order_text': viewpoint_data['viewpointOrderText'],
            }
            enabled_languages = [lang[0] for lang in settings.LANGUAGES]
            for name_translation in viewpoint_data['names']:
                if name_translation['language'] in enabled_languages:
                    vp_attributes['name_%s' % name_translation['language']] = name_translation['value']

            vp, created = AccessibilityViewpoint.objects.get_or_create(
                id=vp_id,
                defaults=vp_attributes
            )
            if created:
                self.stdout.write('Created AccessibilityViewpoint {}'.format(vp.name_en))
            else:
                dirty_fields = self.update_model_attributes(vp, vp_attributes)
                if len(dirty_fields) > 0:
                    vp.save()
                    self.stdout.write('Updated AccessibilityViewpoint {}: {}'.format(
                        vp.name_en, ', '.join(dirty_fields)
                    ))
        # remove viewpoints which did not exist in the source anymore
        AccessibilityViewpoint.objects.exclude(id__in=vp_ids).delete()

    def fetch_resource_accessibility_data(self, base_url):
        """ Populate resource accessibility data from the accessibility API """
        url = "{base_url}/api/v1/accessibility/targets/{system_id}/summary".format(
            base_url=base_url, system_id=settings.RESPA_ACCESSIBILITY_API_SYSTEM_ID)
        data = self.make_request(url)

        for accessibility_data in data:
            try:
                resource = Resource.objects.get(id=accessibility_data['servicePointId'])
                viewpoint = AccessibilityViewpoint.objects.get(id=accessibility_data['viewpointId'])
            except Resource.DoesNotExist:
                # this is normal, the database might contain servicepoints we don't
                # know of
                continue
            except AccessibilityViewpoint.DoesNotExist:
                self.stdout.write('Received unknown Accessibility viewpoint id from API: {}. Skipping.'.format(
                    accessibility_data['viewpointId']))
                continue
            value = self.get_or_create_value(accessibility_data['isAccessible'])
            resource_accessibility, created = ResourceAccessibility.objects.get_or_create(
                resource=resource, viewpoint=viewpoint, defaults={'value': value}
            )
            if created:
                self.stdout.write('Created ResourceAccessibility {}'.format(str(resource_accessibility)))
            else:
                dirty_fields = self.update_model_attributes(resource_accessibility, {'value': value})
                if len(dirty_fields) > 0:
                    resource_accessibility.save()
                    self.stdout.write('Updated ResourceAccessibility {}: {}'.format(
                        str(resource_accessibility), ', '.join(dirty_fields)
                    ))

    def fetch_unit_accessibility_data(self, base_url):
        """ Populate unit accessibility data from the accessibility API.
            Requests only servicepoints we have, the api contains lots of stuff we don't care about.
        """
        url = "{base_url}/api/v1/accessibility/servicepoints/{system_id}/{{servicepoint_id}}/summary".format(
            base_url=base_url, system_id=settings.RESPA_ACCESSIBILITY_API_UNIT_SYSTEM_ID)

        for unit_identifier in UnitIdentifier.objects.filter(namespace='internal').select_related('unit'):
            unit = unit_identifier.unit
            try:
                data = self.make_request(url.format(servicepoint_id=unit_identifier.value))
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 404:
                    # no accessibility data available
                    continue
                raise e

            for viewpoint_data in data:
                try:
                    viewpoint = AccessibilityViewpoint.objects.get(id=viewpoint_data['viewpointId'])
                except AccessibilityViewpoint.DoesNotExist:
                    self.stdout.write('Received unknown Accessibility viewpoint id from API: {}. Skipping.'.format(
                        viewpoint_data['viewpointId']))
                    continue
                value = self.get_or_create_value(viewpoint_data['isAccessible'])
                unit_accessibility, created = UnitAccessibility.objects.get_or_create(
                    unit=unit, viewpoint=viewpoint, defaults={'value': value}
                )
                if created:
                    self.stdout.write('Created UnitAccessibility {}'.format(str(unit_accessibility)))
                else:
                    dirty_fields = self.update_model_attributes(unit_accessibility, {'value': value})
                    if len(dirty_fields) > 0:
                        unit_accessibility.save()
                        self.stdout.write('Updated UnitAccessibility {}: {}'.format(
                            str(unit_accessibility), ', '.join(dirty_fields)
                        ))

    def make_request(self, url):
        try:
            response = requests.get(url, timeout=REQUESTS_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            LOG.exception('Accessibility data import failed. Problem communicating with Accessibility API.')
            raise e
        except ValueError as e:
            LOG.exception('Accessibility data import failed. Response did not contain JSON')
            raise e

    def get_or_create_value(self, value_data):
        """Accessibility API represents accessibility summaries in words like "red", "green"
        default ordering levels set here are
        - green: 10
        - unknown: 0
        - red: -10

        These can be changed later in django admin. Resources which don't have data in Accessibility database
        are considered to have an ordering priority of 0.
        """
        accessibility_value, created = AccessibilityValue.objects.get_or_create(value=value_data)
        if created:
            if accessibility_value.value == 'green':
                accessibility_value.order = 10
                accessibility_value.save()
            elif accessibility_value.value == 'red':
                accessibility_value.order = -10
                accessibility_value.save()
        return accessibility_value

    def update_model_attributes(self, instance, attributes):
        dirty_fields = []
        for key, val in attributes.items():
            if getattr(instance, key) != val:
                dirty_fields.append(key)
                setattr(instance, key, val)
        return dirty_fields
