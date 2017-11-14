import csv
import pytz
import difflib
from pprint import pprint
from collections import OrderedDict
from datetime import datetime

import os
import django
import sys
sys.path.append('../..')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "respa.settings")
django.setup()

from django.db import transaction
from resources.models import Resource, Reservation
from caterings.models import CateringProvider, CateringOrder
from users.models import User

local_tz = pytz.timezone('Europe/Helsinki')


def import_resources():
    resources = {}
    with open('tilat.csv') as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            assert row['TilaId'] not in resources
            row['reservation_count'] = 0
            row['reservations'] = []
            resources[row['TilaId']] = row

    return resources


def import_users():
    users = {}
    with open('kayttaja.csv') as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            if not row['Kayttajatunnus']:
                continue
            assert row['Kayttajatunnus'] not in users
            row['count'] = 0
            users[row['Kayttajatunnus'].lower()] = row

    return users


def import_reservations(resources, users):
    reservations = OrderedDict()
    with open('varaus.csv') as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            if row['TilaId'] not in resources:
                continue
            if row['AlkuAika'] < '2017-11':
                continue
            if row['Poistettu'] != '0':
                continue
            resource = resources[row['TilaId']]
            resource['reservation_count'] += 1
            username = row['Perustaja'].lower()
            if username not in users:
                username = row['Muuttaja'].lower()
                if username not in users:
                    username = None
            user = users.get(username)
            if user:
                user['count'] += 1
            assert row['VarausId'] not in reservations
            row['user'] = user
            row['resource'] = resource
            row['attendees'] = []
            row['catering'] = []
            row['equipment'] = []
            reservations[row['VarausId']] = row
            if not resource['object']:
                continue
            resource['reservations'].append(row)
            #print("%s: %s -> %s: %s" % (resource['Nimi'], row['AlkuAika'], row['LoppuAika'], user['Mail']))
    return reservations


def import_attendees(reservations):
    with open('osallistuja.csv') as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            reservation = reservations.get(row['VarausId'])
            if reservation is None:
                continue
            reservation['attendees'].append(row['Nimi'].strip())


def import_catering(reservations):
    products = {}
    with open('tarjoiltava.csv') as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            products[row['TarjoiltavaId']] = row

    with open('varauksentarjoilu.csv') as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            reservation = reservations.get(row['VarausId'])
            if reservation is None:
                continue
            product = products[row['TarjoiltavaId']]
            reservation['catering'].append(product['Nimi'])


def import_equipment(reservations):
    equipment = {}
    with open('varuste.csv') as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            equipment[row['VarusteId']] = row

    with open('varauksenvarusteet.csv') as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            reservation = reservations.get(row['VarausId'])
            if reservation is None:
                continue
            eq = equipment[row['VarusteId']]
            reservation['equipment'].append(eq['Nimi'])

RESOURCE_MAP = {
    'Kaupunginjohtajan vastaanottohuone': 'avo5xlqtrpca',  # Pormestarin vastaanottohuone
    'Juhlasali / 301': 'avbxbgsac7ha',  # Juhlasali
    'Empiresali / 32': 'avbxastz46ja',  # Empiresali
    'Sofiankabinetti / 12': 'avbxcharbo6q',  # Sofian kabinetti
    'Katariinankabinetti / 12': 'avbxb7j2rc3q',  # Katariinankabinetti
    'Khn istuntosali / 49': 'avo5zeaupfrq',  # Kaupunginhallituksen istuntosali
    'Kvston ravintola / 96': 'avo5zfozbapq',  # Kaupunginvaltuuston ravintola
    'Kvston istuntosali / 120': 'avbxa4zlt7sa',  # Kaupunginvaltuuston istuntosali
    'Aulakabinetti 4 / 18': 'avbxbwlpfckq',  # Aulakabinetti 4
    'Sami Sarvilinna, huone 154B': 'avo5zzo5huga',  # 154 Sarvilinna Sami
    'Summanen Juha 202a / 10': 'avo5z2j3pacq',  # 202 Summanen Juha
    'Kvston puheenjohtaja': 'avo5z3rk43ga',  # 238 Kaupunginvaltuuston puheenjohtaja
    'Sinnemäki Anni': 'avo5z4sitjuq',  # 303 Sinnemäki Anni
    'Razmyar Nasima': 'avo5z5sdyjla',  # 353 Razmyar Nasima
    'Karvinen Marko': 'avo52d6jfeiq',  # 340 Karvinen Marko
    'Sote apri Sanna Vesikansa': 'avo52fcayjtq',  # 350 Vesikansa Sanna
    'Pakarinen Pia': 'avo52fwyk5aq',  # 353 Pakarinen Pia
    'Kvston lähetystöt / 18': 'avbw6nhycqvq',  # Lähetystöhuone
    'Raitio Markku, huone 250': 'avo52io5shda',  # 250 Raitio Markku
    'Auditorio / 78': 'avbxcn4eobuq',  # Auditorio
    'Suuri ruokasali / 10': 'avo52nbuwunq',  # Suuri ruokasali
    'Piraattipuolue / ryhmähuone / 6': 'avbw6yts5e5a',  # Pieni kahvihuone/ Piraattipuolue
    'Sosialidemokraatit / ryhmähuone 234 / 22': 'avbr7smqeghq',  # 234 Sosiaalidemokraatit
    'Svenska folkpartiet / ryhmähuone  236 / 14': 'avbrbq65wlwa',  # 236 Svenska folkpartiet
    'Perussuomalaiset / ryhmähuone 237 / 8': 'avbrcblqsoyq',  # 237 Perussuomalaiset
    'Keskusta / ryhmähuone 239 / 8': 'avbjmwuetuba',  # 239 Keskusta
    'Vasemmistoliitto /ryhmähuone 330 /  14': 'avbw7piv2meq',  # 330 Vasemmistoliitto
    'Kokoomus /ryhmähuone 331 / 30': 'avbw7gwv5mcq',  # 331 Kokoomus
    'Vihreät / ryhmähuone 333 / 28': 'avbbylrg3aga',  # 333 Vihreät
    'Suomen Kristillisdemokraatit 337  / 10': 'avbxaj75iika',  # 337 Suomen Kristillisdemokraatit
    'Unioninkadun neuvotteluhuone 211 /25': 'avnzustammjq',  # 211 neuvotteluhuone
    'Feministinen puolue 335 / 4': 'avbxaaacrv4a',  # 335 Feministinen puolue
}


def determine_resource_mapping(resources):
    units = ['Helsingin kaupungintalo', 'Bockin talo', 'Apteekintalo', 'Burtz-Hellenius']
    res_list = [x.name for x in Resource.objects.filter(public=False).filter(unit__name__in=units)]
    for res in resources.values():
        name = res['Nimi'].split('/')[0].strip()
        matches = difflib.get_close_matches(name, res_list, cutoff=0.5)
        if not matches:
            res['object'] = None
            print("    '%s': None" % (res['Nimi']))
            continue
        res['object'] = Resource.objects.get(unit__name__in=units, name=matches[0])
        upcoming_reservations = res['object'].reservations.filter(begin__gte='2017-11-01').count()
        print("    '%s': '%s', # %s" % (res['Nimi'], res['object'].id, res['object'].name))
        assert not res['object'].public
        assert upcoming_reservations == 0


def set_resource_mapping(resources):
    for res in resources.values():
        obj_id = RESOURCE_MAP.get(res['Nimi'])
        if not obj_id:
            print("No match for %s" % res['Nimi'])
            res['object'] = None
            continue

        obj = Resource.objects.get(id=obj_id)
        existing_reservations = obj.reservations.count()
        print("    '%s': '%s', # %s" % (res['Nimi'], obj.id, obj.name))
        assert not obj.public
        assert existing_reservations == 0

        er = getattr(obj, 'exchange_resource', None)
        if er:
            print("Setting from ER: %s" % obj)
            er.sync_to_respa = False
            er.sync_from_respa = False
            er.save()

        res['object'] = obj

resources = import_resources()
set_resource_mapping(resources)
#determine_resource_mapping(resources)
users = import_users()
reservations = import_reservations(resources, users)
import_attendees(reservations)
import_catering(reservations)
import_equipment(reservations)

user_objects_by_email = {}

PAYER_FIELDS = [
    'MaksajaNimi', 'MaksajaOsoite', 'MaksajaPostiTmp', 'MaksajaPuhelin', 'MaksajaMomentti',
    'MaksajaSelite'
]

catering_provider = CateringProvider.objects.first()
hvara_reservations = {x.origin_id: x for x in Reservation.objects.filter(origin_id__startswith='hvara:')}


def save_reservation(data):
    if not data['resource']['object']:
        return

    origin_id = 'hvara:%s' % data['VarausId']
    res = hvara_reservations.get(origin_id)
    try:
        res = Reservation.objects.get(origin_id=origin_id)
    except Reservation.DoesNotExist:
        res = Reservation(origin_id=origin_id)

    res.begin = local_tz.localize(datetime.strptime(data['AlkuAika'], "%Y-%m-%dT%H:%M:%S"))
    res.end = local_tz.localize(datetime.strptime(data['LoppuAika'], "%Y-%m-%dT%H:%M:%S"))
    res.event_subject = data['Tilaisuus'].strip()
    res.host_name = data['Isanta'].strip()
    res.created_at = local_tz.localize(datetime.strptime(data['Perustettu'], "%Y-%m-%dT%H:%M:%S"))
    res.modified_at = local_tz.localize(datetime.strptime(data['Muutettu'], "%Y-%m-%dT%H:%M:%S"))
    res.number_of_participants = int(data['OsallistujaLkm'])
    res.event_description = data['Selite'] or ''
    if data['VarusteluSelite']:
        res.event_description += 'Varustelu:\n' + data['VarusteluSelite']
    res.participants = '\n'.join(data['attendees'])
    if data['OsallistujaSelite']:
        if res.participants:
            res.participants += '\n\n'
        res.participants += data['OsallistujaSelite']
    res.comments = 'Siirretty vanhasta huonevarausjärjestelmästä'
    res.resource = data['resource']['object']

    user = data['user']
    res.reserver_name = user['Nimi']
    email = user['Mail'].strip().lower()
    res.reserver_email_address = email
    res.reserver_phone_number = user['Puhelin']

    if email not in user_objects_by_email:
        try:
            u_obj = User.objects.get(email=email)
        except User.DoesNotExist:
            print("%s does not exist" % email)
            u_obj = None
        res.user = u_obj
        user_objects_by_email[email] = u_obj

    res._skip_notifications = True
    res.save()
    print(res)

    if data['catering'] or data['TarjoiluSelite']:
        order = CateringOrder(reservation=res, provider=catering_provider)
        invoicing_data = [data.get(f) for f in PAYER_FIELDS]
        order.invoicing_data = '\n'.join([val.strip() for val in invoicing_data if val])
        message_data = []
        if data['catering']:
            message_data.append('\n'.join(data['catering']))
        if data['TarjoiluSelite']:
            message_data.append(data['TarjoiluSelite'].strip())
        order.message = '\n\n'.join(message_data)
        order.save()


@transaction.atomic
def save_reservations(reservations):
    for res in reservations.values():
        save_reservation(res)
        continue

        r2 = res.copy()
        del r2['resource']
        fields = [
            'VarusteluSelite',
        ]
        output = OrderedDict()
        for f in fields:
            val = r2.get(f)
            if val:
                output[f] = val
        if output:
            print(r2['Tilaisuus'])
            for key, val in output.items():
                print("\t%s: %s" % (key, val))
        #pprint(r2)


save_reservations(reservations)


resource_counts = []
for res in resources.values():
    if not res['reservation_count']:
        continue
    #print("%s: %s" % (user['Mail'], user['count']))
    resource_counts.append((res['Nimi'], res['reservation_count']))

for m, c in sorted(resource_counts, key=lambda x: x[1], reverse=True):
    print("%s\t%s" % (c, m))

users_and_counts = []
for user in users.values():
    if not user['count']:
        continue
    #print("%s: %s" % (user['Mail'], user['count']))
    users_and_counts.append((user['Mail'], user['count']))

for m, c in sorted(users_and_counts, key=lambda x: x[1], reverse=True):
    print("%s\t%s" % (m, c))
