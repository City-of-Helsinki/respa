import csv
import datetime

import requests

import io
from django.core.exceptions import ObjectDoesNotExist
from ..models import Purpose, Resource, ResourceType, Unit
from .base import Importer, register_importer


@register_importer
class Kirjasto10Importer(Importer):
    name = "kirjasto10"
    RESOURCETYPE_IDS = {'työtila': 'workspace',
                    'työpiste': 'workstation',
                    'tapahtumatila': 'event_space',
                    'studio': 'studio',
                    'näyttelytila': 'exhibition_space',
                    'kokoustila': 'meeting_room',
                    'pelitila': 'game_space'}
    AUTHENTICATION = {'Ei tunnistautumista': 'none',
                          'Kevyt': 'weak',
                          'Vahva': 'strong'}
    PURPOSE_IDS = {}
    PURPOSE_IDS['audiovisual_work'] = {'laulaminen / musiikin soitto ja äänitys': 'sing_play_and_record_music',
                                          'äänen käsittely tietokoneella': 'edit_sound',
                                          'kuvan käsittely tietokoneella': 'edit_image',
                                          'videokuvan käsittely tietokoneella': 'edit_video',
                                          'digitointi': 'digitizing'}
    PURPOSE_IDS['physical_work'] = {'fyysisten esineiden tekeminen': 'manufacturing'}
    PURPOSE_IDS['watch_and_listen']= {'(elokuvien) katselu': 'watch_video',
                                         'musiikin kuuntelu': 'listen_to_music'}
    PURPOSE_IDS['meet_and_work'] = {'kokoukset, suljetut tilaisuudet': 'private_meetings',
                                       'työskentely ryhmässä': 'work_in_group',
                                       'työskentely yksin': 'work_alone',
                                       'tietokoneen käyttäminen': 'work_at_computer'}
    PURPOSE_IDS['games'] = {'konsolipelit': 'console_games',
                               'pelaaminen: lauta-, kortti- ja roolipelit': 'board_card_and_role_playing_games',
                               'tietokonepelit': 'computer_games'}
    PURPOSE_IDS['events_and_exhibitions'] = {'näyttelyt': 'exhibitions',
                                                'yleisötilaisuudet, tapahtumat': 'public_events'}

    def import_resources(self):
        url = "https://docs.google.com/spreadsheets/d/1dOlIIDUINfOdyrth42JmQyTDzJmZJbwTi_bqMxRm7i8/export?format=csv&id=1dOlIIDUINfOdyrth42JmQyTDzJmZJbwTi_bqMxRm7i8&gid=0"
        resp = requests.get(url)
        assert resp.status_code == 200
        reader = csv.DictReader(io.StringIO(resp.content.decode('utf8')))
        next(reader)  # remove field descriptions
        data = list(reader)

        missing_units = set()

        for res_data in data:
            unit_name = res_data['Osasto']
            try:
                unit = Unit.objects.get(name_fi=unit_name)
            except ObjectDoesNotExist:
                # No unit for this resource in the db
                if unit_name not in missing_units:
                    print("Unit %s not found in db" % unit_name)
                    missing_units.add(unit_name)
                continue

            if res_data['Erillisvaraus'] is 'Kyllä':
                confirm = True
            else:
                confirm = False
            try:
                area = int(res_data['Koko m2'])
            except ValueError:
                area = None
            try:
                people_capacity = int(res_data['Henkilömäärä'])
            except ValueError:
                people_capacity = None
            try:
                min_period = datetime.timedelta(minutes=int(60*float(res_data['Varausaika min'].replace(',', '.'))))
            except ValueError:
                min_period = datetime.timedelta(minutes=30)
            try:
                max_period = datetime.timedelta(minutes=int(60*float(res_data['Varausaika max'].replace(',', '.'))))
            except ValueError:
                max_period = None

            resource_name = self.clean_text(res_data['Nimi'])

            data = dict(
                unit_id=unit.pk,
                people_capacity=people_capacity,
                area=area,
                need_manual_confirmation=confirm,
                min_period=min_period,
                max_period=max_period,
                authentication=self.AUTHENTICATION[res_data['Asiakkuus / tunnistamisen tarve']]
            )
            data['name'] = {'fi': resource_name}
            data['description'] = {'fi': self.clean_text(res_data['Kuvaus'])}

            data['purposes'] = []
            purposes = [res_data[key] for key in res_data if key.startswith('Käyttötarkoitus')]
            for purpose in purposes:
                if not purpose:
                    continue

                main_type = [key for key in self.PURPOSE_IDS if purpose in self.PURPOSE_IDS[key].keys()][0]

                purpose_id = self.PURPOSE_IDS[main_type][purpose]
                try:
                    purpose_obj = Purpose.objects.get(id=purpose_id)
                except Purpose.DoesNotExist:
                    purpose_obj = Purpose(id=purpose_id)

                purpose_obj.name_fi = purpose
                purpose_obj.main_type = main_type
                purpose_obj.save()

                data['purposes'].append(purpose_obj)

            res_type_id = self.RESOURCETYPE_IDS[res_data['Tilatyyppi']]
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
