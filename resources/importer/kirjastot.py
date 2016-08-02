import datetime
from collections import namedtuple

import requests
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from psycopg2.extras import DateRange
import delorean
from django.db import transaction

from ..models import Unit, UnitIdentifier
from .base import Importer, register_importer

ProxyPeriod = namedtuple("ProxyPeriod",
                         ['start',
                          'end',
                          'description',
                          'closed',
                          'name',
                          'unit',
                          'days'])


@register_importer
class KirjastotImporter(Importer):

    """
    Importer tries to convert kirjastot.fi opening hours information to into database

    Since Respa has somewhat stricter rules for Period overlaps, this requires some fiddling

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
        # TODO: Fix importer for problematic libraries 8294 and 8324
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
            if unit.id in ["tprek:8294", "tprek:8324"]:
                continue
            unit.periods.all().delete()
            periods = []
            for period in unit_data['periods']:
                if not period['start'] or not period['end']:
                    continue  # NOTE: period is supposed to have *at least* start or end date
                start = datetime.datetime.strptime(period['start'], '%Y-%m-%d').date()
                if not period['end']:
                    this_day = datetime.date.today()
                    end = datetime.date(this_day.year + 1, 12, 31)  # No end time goes to end of next year
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
            d_range = DateRange(period.start, period.end, '[]')
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

        print("debug save", period.start, period.end, parent, period.unit)

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


class ImportingException(Exception):
    pass


@transaction.atomic
def process_varaamo_libraries():
    """
    Find varaamo libraries' Units from the db,
    ask their data from kirjastot.fi and
    process resulting opening hours if found
    into their Unit object

    TODO: Libraries in Helmet system with resources need more reliable identifier

    :return: None
    """
    varaamo_units = Unit.objects.filter(identifiers__namespace="helmet").exclude(resources__isnull=True)



    for varaamo_unit in varaamo_units:
        data = timetable_fetcher(varaamo_unit)
        if data:
            try:
                with transaction.atomic():
                    varaamo_unit.periods.all().delete()
                    process_periods(data, varaamo_unit)
            except Exception as e:
                print("Problem in processing data of library ", varaamo_unit, e)
        else:
            print("Failed data fetch on library: ", varaamo_unit)


def timetable_fetcher(unit, start='2016-07-01', end='2016-12-31'):
    """
    Fetch periods using kirjastot.fi's new v3 API

    v3 gives opening for each day with period id
    it originated from, thus allowing creation of
    unique periods

    TODO: helmet consortium's id permanency check

    :param unit: Unit object of the library
    :param start: start day for required opening hours
    :param end: end day for required opening hours
    :return: dict|None
    """

    base = "https://api.kirjastot.fi/v3/organisation"

    for identificator in unit.identifiers.filter(namespace="helmet"):
        params = {
            "identificator": identificator.value,
            "consortium": "2093",  # TODO: Helmet consortium id in v3 API
            "with": "extra,schedules",
            "period.start": start,
            "period.end": end
        }

        resp = requests.get(base, params=params)

        if resp.status_code == 200:
            data = resp.json()
            if data["total"] > 0:
                return data
            else:
                # There's possibly other identificators that might work
                continue
        else:
            return False

    # No timetables were found :(
    return False


def process_periods(data, unit):
    """
    Generate Period and Day objects into
    given Unit from kirjastot.fi v3 API data

    Each day in data has its own Period and Day object
    resulting in as many Periods with one Day as there is
    items in data

    :param data: kirjastot.fi v3 API data form /organisation endpoint
    :param unit: Unit
    :return: None
    """

    periods = []
    for period in data['items'][0]['schedules']:
        periods.append({
            'date': period.get('date'),
            'day': period.get('day'),
            'opens': period.get('opens'),
            'closes': period.get('closes'),
            'closed': period['closed'],
            'description': period['info']['fi']
        })

    for period in periods:
        nper = unit.periods.create(
            start=period.get('date'),
            end=period.get('date'),
            description=period.get('description'),
            closed=period.get('closed') or False,
            name=period.get('description') or ''
        )

        nper.days.create(weekday=int(period.get('day')) - 1,
                         opens=period.get('opens'),
                         closes=period.get('closes'),
                         closed=period.get('closed'))

        # TODO: automagic closing checker
        # One day equals one period and share same closing state
        nper.closed = period.get('closed')
        nper.save()


def period_sorter(period):
    """
    Period's sorting keys

    TODO: check significance spec: first by length, then by closed state

    :param period: ProxyPeriod
    :return: (datetime.timedelta, bool)
    """
    return period.end - period.start, not period.closed


def merger(data):
    """
    Sort kirjastot.fi periods by significance
    from low to high

    TODO: check significance spec: first by length, then by closed state
    :param data: kirjastot.fi data
    :return: [ProxyPeriod]
    """
    Unit.objects.get(pk='tprek:8199')
    u = Unit.objects.get(pk='tprek:8199')
    vallila = [j for j in data if j['identificator'] == 'H55'][0]
    periods = []
    for period in vallila['periods']:
        if not period['start'] or not period['end']:
            continue  # NOTE: period is supposed to have *at least* start or end date
        start = datetime.datetime.strptime(period['start'], '%Y-%m-%d').date()
        if not period['end']:
            this_day = datetime.date.today()
            end = datetime.date(this_day.year + 1, 12, 31)  # No end time goes to end of next year
        else:
            end = datetime.datetime.strptime(period['end'], '%Y-%m-%d').date()
        periods.append(ProxyPeriod(
            orig=None,
            start=start,
            end=end,
            description=period['description']['fi'],
            closed=period['closed'],
            name=period['name']['fi'],
            unit=u,
            days=period['days']
        ))
    return reversed(sorted(periods, key=period_sorter))


def time_machine(periods):
    """
    Creates a dict of where keys are days
    and values ProxyPeriod objects governing those days

    Assuming periods are sorted from least to highest
    significance, this results in opening hours data
    for all days accounted for by periods combined

    :param periods:[ProxyPeriod]
    :return: {datetime.date:ProxyPeriod}
    """
    days_of_our_lives = {}

    for period in periods:
        start = datetime.datetime.combine(
            period.start, datetime.time(0, 0))
        end = datetime.datetime.combine(
            period.end, datetime.time(23, 59))
        for stop in delorean.stops(
                freq=delorean.DAILY, start=start, stop=end):
            days_of_our_lives[stop.date] = period

    return days_of_our_lives


def periodic_progress(day_times):
    """

    Sort day_times by its keys that should be date objects

    Take first day's period and add it to governing_periods list
    because that's first day's governing period

    Loop through sorted day_times

    For every you get a date object and a period
    Now get previous day's period object from day_times
    (this is None for the first iteration, but you got to check)

    Compare today and yesterday and you'll see if a boundary has been found

    If this is the case retrieve currently governing period
    (that has a the correct start time but now wrong end time)

    Now replace last governing period in the list with
    a ProxyPeriod object using previous governing period and
    day_times original yesterday's period start and end days
    respectively

    This sets that period with a start day as before and
    end date to yesterday, day before today's new governing period

    Then get that period and add it to governing periods,
    but replace its start day (which might be anything from today to
    distant past) with today (since at this span the period
    can only govern from this day forward till the start of next
    period)

    Repeat till all the days of the day_times dict have been called for,
    resulting in ProxyPeriod objects that are actually in effect and not
    the data they had when they came in (because in kirjastot.fi they
    can have overlapping day spans)

    :param day_times:{datetime.date: ProxyPeriod}
    :return:[ProxyPeriod]
    """

    governing_periods = []

    periods_in_order = list(sorted(
        day_times.items(),
        key=lambda x: x[0]))

    governing_periods.append(periods_in_order[0][1])

    minus_day = datetime.timedelta(days=1)

    for day, today_period in periods_in_order:

        yesterday_period = day_times.get(day - minus_day)

        if yesterday_period and today_period != yesterday_period:

            if yesterday_period.start == yesterday_period.end:
                new_yesterday_period_end = yesterday_period.end
            else:
                new_yesterday_period_end = day - datetime.timedelta(days=1)

            currently_governing_period = governing_periods[len(governing_periods) - 1]

            governing_periods[len(governing_periods) - 1] = ProxyPeriod(
                orig=currently_governing_period,
                start=currently_governing_period.start,
                end=new_yesterday_period_end,
                description=yesterday_period.description,
                closed=yesterday_period.closed,
                name=yesterday_period.name,
                unit=yesterday_period.unit,
                days=yesterday_period.days
            )

            governing_periods.append(ProxyPeriod(
                orig=today_period,
                start=day,
                end=today_period.end,
                description=today_period.description,
                closed=today_period.closed,
                name=today_period.name,
                unit=today_period.unit,
                days=today_period.days
            ))

        else:
            continue

    return governing_periods
