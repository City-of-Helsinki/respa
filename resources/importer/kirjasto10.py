import csv
import requests
import io
import datetime
from pprint import pprint

from .base import Importer, register_importer
from ..models import Unit, UnitIdentifier, Period, Resource, ResourceType, Purpose
from django.core.exceptions import ObjectDoesNotExist, ValidationError


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
    PURPOSE_IDS['audiovisual_work'] = {'musiikin soitto ja äänitys': 'play_and_record_music',
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

        for res_data in data:
            res_type, created = ResourceType.objects.get_or_create(
                # TODO: Catch key error if resource type unknown
                id=self.RESOURCETYPE_IDS[res_data['Tilatyyppi']],
                name_fi=self.clean_text(res_data['Tilatyyppi']),
                main_type='space')

            try:
                unit = Unit.objects.get(name_fi=res_data['Osasto'])
            except ObjectDoesNotExist:
                # No unit for this resource in the db
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

            res, created = unit.resources.get_or_create(
                #  TODO: Better ids here also, without this invalid resource objects gets created
                id=res_data['Nimi'],
                type=res_type,
                name_fi=self.clean_text(res_data['Nimi']),
                people_capacity=people_capacity,
                area=area,
                need_manual_confirmation=confirm,
                description_fi=self.clean_text(res_data['Kuvaus']),
                min_period=min_period,
                max_period=max_period,
                authentication=self.AUTHENTICATION[res_data['Asiakkuus / tunnistamisen tarve']]
            )

            purposes = [res_data[key] for key in res_data if key.startswith('Käyttötarkoitus')]
            for purpose in purposes:
                if purpose:
                    main_type = [key for key in self.PURPOSE_IDS if (purpose in self.PURPOSE_IDS[key].keys())][0]
                    pprint(self.PURPOSE_IDS[main_type][purpose])
                    res_purpose, created = Purpose.objects.get_or_create(
                        # TODO: Catch key error if purpose unknown
                        id=self.PURPOSE_IDS[main_type][purpose],
                        name_fi=purpose,
                        main_type=main_type
                    )
                    res.purposes.add(res_purpose)
                    pprint("purpose " + purpose + " added to " + str(res))
