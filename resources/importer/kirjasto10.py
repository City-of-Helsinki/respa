import csv
import requests
import io
from pprint import pprint

from .base import Importer, register_importer
from ..models import Unit, Resource, ResourceType


@register_importer
class Kirjasto10Importer(Importer):
    name = "kirjasto10"

    def import_resources(self):
        unit = Unit.objects.get(name_fi='Kirjasto 10')
        print(unit)
        url = "https://docs.google.com/spreadsheets/d/1dOlIIDUINfOdyrth42JmQyTDzJmZJbwTi_bqMxRm7i8/export?format=csv&id=1dOlIIDUINfOdyrth42JmQyTDzJmZJbwTi_bqMxRm7i8&gid=0"
        resp = requests.get(url)
        assert resp.status_code == 200
        reader = csv.DictReader(io.StringIO(resp.content.decode('utf8')))
        for res_data in reader:
            pprint(res_data)
