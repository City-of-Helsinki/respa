import csv
import datetime
import io

import requests
from django.core.exceptions import ObjectDoesNotExist
from django.utils.text import slugify
from ..models import Purpose, Resource, ResourceType, Unit
from .base import Importer, register_importer


@register_importer
class Kirjasto10Importer(Importer):
    name = "kirjasto10"
    RESOURCETYPE_IDS = {
        'työtila': 'workspace',
        'työpiste': 'workstation',
        'tapahtumatila': 'event_space',
        'studio': 'studio',
        'näyttelytila': 'exhibition_space',
        'kokoustila': 'meeting_room',
        'pelitila': 'game_space',
        'liikuntatila': 'sports_space',
        'sali': 'hall',
        'bändikämppä': 'band_practice_space',
        'monitoimihuone': 'multipurpose_room',
        'kerhohuone': 'club_room',
        'ateljee': 'art_studio',
        'keittiö': 'kitchen',
        'ryhmävierailu': 'group_visit'
    }
    AUTHENTICATION = {
        'Ei tunnistautumista': 'none',
        'Kevyt': 'weak',
        'Vahva': 'strong'
    }

    def import_resources(self):
        # First, create the purpose hierarchy:
        purpose_url = "https://docs.google.com/spreadsheets/d/1mjeCSLQFA82mBvGcbwPkSL3OTZx1kaZtnsq3CF_f4V8/export?format=csv&id=1mjeCSLQFA82mBvGcbwPkSL3OTZx1kaZtnsq3CF_f4V8&gid=1039480682"
        resp = requests.get(purpose_url)
        assert resp.status_code == 200
        print(str(resp.content))
        reader = csv.reader(io.StringIO(resp.content.decode('utf8')))
        data = list(reader)
        print(str(data))
        parent = ''
        for purp_data in data:
            if purp_data[0]:
                # create parent purpose
                parent_fi = purp_data[0]
                parent_en = purp_data[2]
                parent, created = Purpose.objects.get_or_create(id=slugify(parent_en), defaults={
                    'name_fi': parent_fi,
                    'name_en': parent_en,
                    'parent': None,
                })
            # create purpose
            name_fi = purp_data[1]
            name_en = purp_data[3]
            purpose, created = Purpose.objects.get_or_create(id=slugify(name_en), defaults={
                'name_fi': name_fi,
                'name_en': name_en,
                'parent': parent,
            })


        url = "https://docs.google.com/spreadsheets/d/1mjeCSLQFA82mBvGcbwPkSL3OTZx1kaZtnsq3CF_f4V8/export?format=csv&id=1mjeCSLQFA82mBvGcbwPkSL3OTZx1kaZtnsq3CF_f4V8&gid=0"
        resp = requests.get(url)
        assert resp.status_code == 200
        reader = csv.DictReader(io.StringIO(resp.content.decode('utf8')))
        next(reader)  # remove field descriptions
        data = list(reader)

        missing_units = set()

        for res_data in data:
            unit_name = res_data['Osasto']
            try:
                unit = Unit.objects.get(name_fi__iexact=unit_name)
            except ObjectDoesNotExist:
                # No unit for this resource in the db
                if unit_name not in missing_units:
                    print("Unit %s not found in db" % unit_name)
                    missing_units.add(unit_name)
                continue

            if res_data['Erillisvaraus'] == 'Kyllä':
                confirm = True
            else:
                confirm = False
            try:
                area = int(res_data['Koko m2'])
            except ValueError:
                area = None
            try:
                people_capacity = int(res_data['Max henkilömäärä'])
            except ValueError:
                people_capacity = None
            try:
                min_period = datetime.timedelta(minutes=int(60 * float(res_data['Varausaika min'].replace(',', '.'))))
            except ValueError:
                min_period = datetime.timedelta(minutes=30)
            try:
                max_period = datetime.timedelta(minutes=int(60 * float(res_data['Varausaika max'].replace(',', '.'))))
            except ValueError:
                max_period = None
            try:
                max_reservations_per_user = int(res_data['Max. varaukset per tila (voimassa olevat)'])
            except ValueError:
                max_reservations_per_user = None
            reservable = True if res_data['Varattavuus'] == 'Kyllä' else False
            try:
                reservation_info = res_data['Varausinfo / kirjautunut']
            except ValueError:
                reservation_info = None

            resource_name = self.clean_text(res_data['Nimi'])

            data = dict(
                unit_id=unit.pk,
                people_capacity=people_capacity,
                area=area,
                need_manual_confirmation=confirm,
                min_period=min_period,
                max_period=max_period,
                authentication=self.AUTHENTICATION[res_data['Asiakkuus / tunnistamisen tarve']],
                max_reservations_per_user=max_reservations_per_user,
                reservable=reservable,
                reservation_info=reservation_info,
            )
            data['name'] = {'fi': resource_name}
            data['description'] = {'fi': self.clean_text(res_data['Kuvaus'])}

            data['purposes'] = []
            purposes = [res_data[key] for key in res_data if key.startswith('Käyttötarkoitus')]
            for purpose in purposes:
                if not purpose:
                    continue
                try:
                    purpose_obj = Purpose.objects.get(name_fi=purpose)
                    data['purposes'].append(purpose_obj)
                except Purpose.DoesNotExist:
                    print('Purpose %s not found' % purpose)

            res_type_id = self.RESOURCETYPE_IDS[res_data['Tilatyyppi'].lower()]
            try:
                res_type = ResourceType.objects.get(id=res_type_id)
            except ResourceType.DoesNotExist:
                res_type = ResourceType(id=res_type_id)
            res_type.name_fi = self.clean_text(res_data['Tilatyyppi'])
            res_type.main_type = 'space'
            res_type.save()

            data['type_id'] = res_type.pk

            try:
                resource = Resource.objects.get(unit=unit, name_fi=resource_name)
            except Resource.DoesNotExist:
                resource = None

            self.save_resource(data, resource)
