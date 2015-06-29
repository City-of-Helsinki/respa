import requests
import datetime

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

        import json
        s = json.load(open('kirdata.json'))
        data = [s.pop()]

        for unit_data in data:
            id_qs = UnitIdentifier.objects.filter(namespace='helmet', value=unit_data['identificator'])
            unit = Unit.objects.get(identifiers=id_qs)
            print("que", unit)
            for period in unit_data['periods']:
                start = datetime.datetime.strptime(period['start'], '%Y-%m-%d')
                end = datetime.datetime.strptime(period['end'], '%Y-%m-%d')
                active_period, created = unit.periods.get_or_create(
                    start=start,
                    end=end,
                    description=period['description']['fi'],
                    closed=period['closed'],
                    name=period['name']['fi']
                )
                for day_id, day in period['days'].items():
                    try:
                        opens = int(day['opens'].replace(':', ''))
                        closes = int(day['closes'].replace(':', ''))
                    except ValueError:
                        # Either hours missing or corrupt
                        # TODO: check the data for inconsistencies
                        opens, closes = None, None
                    active_period.days.get_or_create(
                        weekday=day['day'],
                        opens=opens,
                        closes=closes,
                        closed=day['closed']
                    )
