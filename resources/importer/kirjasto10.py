import csv
import requests
import io
from pprint import pprint

from .base import Importer, register_importer
from ..models import Unit, UnitIdentifier, Period, Resource, ResourceType
from django.core.exceptions import ObjectDoesNotExist, ValidationError


@register_importer
class Kirjasto10Importer(Importer):
    name = "kirjasto10"

    def import_resources(self):
        url = "https://docs.google.com/spreadsheets/d/1dOlIIDUINfOdyrth42JmQyTDzJmZJbwTi_bqMxRm7i8/export?format=csv&id=1dOlIIDUINfOdyrth42JmQyTDzJmZJbwTi_bqMxRm7i8&gid=0"
        resp = requests.get(url)
        assert resp.status_code == 200
        reader = csv.DictReader(io.StringIO(resp.content.decode('utf8')))
        data = list(reader)

        for res_data in data:
            res_type, created = ResourceType.objects.get_or_create(
                #  TODO: Better ids, without this invalid resource objects gets created
                id=res_data['Tilatyyppi 1'],
                name=res_data['Tilatyyppi 1'],
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

            res, created = unit.resources.get_or_create(
                #  TODO: Better ids here also, without this invalid resource objects gets created
                id=res_data['Nimi'],
                type=res_type,
                name=res_data['Nimi'],
                people_capacity=people_capacity,
                area=area,
                need_manual_confirmation=confirm,
                description=res_data['Kuvaus']
            )
