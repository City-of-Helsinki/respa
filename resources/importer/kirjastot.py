import requests

from .base import Importer, register_importer
from ..models import Unit, UnitIdentifier, Period


@register_importer
class KirjastoImporter(Importer):
    name = "kirjasto"

    def import_units(self):
        print("Fetching units")
        url = "http://api.kirjastot.fi/..."
        # resp = requests.get(url)
        # assert resp.status_code == 200
        # data = resp.json()  # ??

        data = [{'id': 'H53', 'periods': []}]

        for unit_data in data:
            id_qs = UnitIdentifier.objects.filter(namespace='helmet', value=unit_data['id'])
            unit = Unit.objects.get(identifiers=id_qs)
            print(unit)
            periods = unit.periods.all()
