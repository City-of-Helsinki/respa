import requests
import datetime
from django.core.exceptions import ObjectDoesNotExist, ValidationError

from .base import Importer, register_importer
from ..models import Unit, UnitIdentifier, Period


@register_importer
class KirjastoImporter(Importer):
    name = "kirjasto"

    def import_units(self):
        print("Fetching units")
        url = "http://api.kirjastot.fi/v2/search/libraries?consortium=helmet&with=periods"
        resp = requests.get(url)
        assert resp.status_code == 200
        data = resp.json()  # ??

        # data = [{'id': 'H53', 'periods': []}]

        for unit_data in data:
            id_qs = UnitIdentifier.objects.filter(namespace='helmet', value=unit_data['identificator'])
            try:
                unit = Unit.objects.get(identifiers=id_qs)
            except ObjectDoesNotExist:
                continue
            for period in unit_data['periods']:
                if not period['start'] or not period['end']:
                    continue  # NOTE: period is supposed to have *at least* start or end date
                start = datetime.datetime.strptime(period['start'], '%Y-%m-%d')
                if not period['end']:
                    this_day = datetime.date.today()
                    end = datetime.date(this_day.year + 1 , 12, 31) # No end time goes to end of next year
                else:
                    end = datetime.datetime.strptime(period['end'], '%Y-%m-%d')
                active_period, created = unit.periods.get_or_create(
                    start=start,
                    end=end,
                    description=period['description']['fi'],
                    closed=period['closed'],
                    name=period['name']['fi']
                )
                if not period['days']:
                    continue
                for day_id, day in period['days'].items():
                    try:
                        # TODO: check the data for inconsistencies
                        opens = day['opens'] or None
                        closes = day['closes'] or None
                        active_period.days.get_or_create(
                            weekday=day['day'],
                            opens=opens,
                            closes=closes,
                            closed=day['closed']
                        )
                    except ValidationError as e:
                        print(e)
                        print(day)
                        return None
