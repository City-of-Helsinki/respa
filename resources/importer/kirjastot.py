import datetime
from collections import namedtuple

import requests
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from psycopg2.extras import DateRange, DateTimeTZRange, NumericRange

from ..models import Period, Unit, UnitIdentifier
from .base import Importer, register_importer

ProxyPeriod = namedtuple("ProxyPeriod", ['start', 'end', 'description', 'closed', 'name', 'unit', 'days'])

@register_importer
class KirjastotImporter(Importer):

    """
    Importer tries to convert kirjastot.fi opening hours information to into database

    Since respa has somewhat stricter rules for Period overlaps, this requires some fidling

    If period is fully overlapping existing, larger period, the new one becomes its exception

    If period overlaps only partially, there is attempt to split it to overlapping and non-overlapping
    parts and then tried again
    In ideal case this results in exception being created for overlapping part, and regular period
    for non-overlapping part

    Overlaps more than two levels deep (exception's exception) are not handled at the moment, nor
    period that overlaps on two periods at the same time

    TODO: check more carefully that importer does the right things and add more tests
    """
    name = "kirjastot"

    def import_units(self):
        print("hrm")
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
            print(unit)
            unit.periods.all().delete()
            periods = []
            for period in unit_data['periods']:
                if not period['start'] or not period['end']:
                    continue  # NOTE: period is supposed to have *at least* start or end date
                start = datetime.datetime.strptime(period['start'], '%Y-%m-%d').date()
                if not period['end']:
                    this_day = datetime.date.today()
                    end = datetime.date(this_day.year + 1 , 12, 31) # No end time goes to end of next year
                else:
                    end = datetime.datetime.strptime(period['end'], '%Y-%m-%d').date()
                periods.append(ProxyPeriod(
                    start=start,
                    end=end,
                    description=period['description']['fi'],
                    closed=period['closed'],
                    name=period['name']['fi'],
                    unit=unit,
                    days=period['days']
                ))

            self.handle_periods(periods)

    def handle_periods(self, periods):

        exceptional_periods = []

        for period in sorted(periods, key=lambda x: x.end - x.start, reverse=True):
            try:
                self.save_period(period)
            except ValidationError:
                exceptional_periods.append(period)

        self.handle_exceptional_periods(exceptional_periods)

    def handle_exceptional_periods(self, exceptional_periods, split=False):

        if split:
            print("debug handling split period")

        for period in exceptional_periods:

            if period.start == period.end:
                # DateRange must end at least one day after its start
                d_range = DateRange(period.start, period.end + datetime.timedelta(days=+1))
            else:
                d_range = DateRange(period.start, period.end)

            overlapping_periods = period.unit.periods.filter(duration__overlap=d_range)

            if len(overlapping_periods) == 1:
                try:
                    self.save_period(period, parent=overlapping_periods[0])
                except ValidationError as e:
                    print("failing overlapping period save", period, overlapping_periods, e)
                    self.split_period(period, overlapping_periods[0])
            else:
                if overlapping_periods:
                    print("debug overlapping periods", overlapping_periods)

    def split_period(self, period, overlapping_period):

        if period.start < overlapping_period.start and period.end < overlapping_period.end:

            # exceptional period overlapping original on the left, starting side

            before_start = period.start
            before_end = overlapping_period.start
            after_start = overlapping_period.start
            after_end = period.end

        elif period.start > overlapping_period.start and period.end > overlapping_period.end:

            # exceptional period overlapping original on the right, ending side

            before_start = period.start
            before_end = overlapping_period.end
            after_start = overlapping_period.end
            after_end = period.end

        else:
            print("failed to split period", period, overlapping_period)
            return None

        before = ProxyPeriod(
            start=before_start,
            end=before_end,
            description=period.description,
            closed=period.closed,
            name=period.name,
            unit=period.unit,
            days=period.days
        )

        after = ProxyPeriod(
            start=after_start,
            end=after_end,
            description=period.description,
            closed=period.closed,
            name=period.name,
            unit=period.unit,
            days=period.days
        )

        self.handle_exceptional_periods([before, after], split=True)

    def save_period(self, period, parent=None):

        print("debug save", period.start, period.end, parent)

        if parent:

            active_period = period.unit.periods.create(
                    start=period.start,
                    end=period.end,
                    description=period.description,
                    closed=period.closed,
                    name=period.name,
                    parent=parent,
                    exception=True)

        else:

            active_period = period.unit.periods.create(
                    start=period.start,
                    end=period.end,
                    description=period.description,
                    closed=period.closed,
                    name=period.name)

        if period.days:
            for day_id, day in period.days.items():
                weekday = day['day'] - 1
                try:
                    # TODO: check the data for inconsistencies
                    opens = day['opens'] or None
                    closes = day['closes'] or None
                    active_period.days.create(
                        weekday=weekday,
                        opens=opens,
                        closes=closes,
                        closed=day['closed']
                    )
                except ValidationError as e:
                    print(e)
                    print(day)
                    return None
