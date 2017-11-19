import datetime
from collections import namedtuple
import calendar, datetime

import requests
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from psycopg2.extras import DateRange
import delorean
from django.db import transaction
from django.db.models import Q

from resources.models import Unit, UnitIdentifier
from .base import Importer, register_importer

from raven import Client

from django.conf import settings

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
    name = "kirjastot"

    def import_units(self):
        get_helmet_timetables()
        process_varaamo_libraries()


class ImportingException(Exception):
    pass


@transaction.atomic
def process_varaamo_libraries():
    """
    Find varaamo libraries' Units from the db,
    ask their data from kirjastot.fi and
    process resulting opening hours if found
    into their Unit object

    Asks the span of opening hours from get_time_range

    TODO: Libraries in Helmet system with resources need more reliable identifier

    :return: None
    """
    varaamo_units = Unit.objects.filter(identifiers__namespace="kirjastot.fi").exclude(resources__isnull=True)

    start, end = get_time_range()
    problems = []
    for varaamo_unit in varaamo_units:
        data = timetable_fetcher(varaamo_unit, start, end)
        if data:
            try:
                with transaction.atomic():
                    varaamo_unit.periods.all().delete()
                    process_periods(data, varaamo_unit)
                    varaamo_unit.update_opening_hours()
            except Exception as e:
                print("Problem in processing data of library ", varaamo_unit, e)
                problems.append(" ".join(["Problem in processing data of library ", str(varaamo_unit), str(e)]))
        else:
            print("Failed data fetch on library: ", varaamo_unit)
            problems.append(" ".join(["Failed data fetch on library: ", str(varaamo_unit)]))

    try:
        if problems and settings.RAVEN_DSN:
            # Report problems to Raven/Sentry
            client = Client(settings.RAVEN_DSN)
            client.captureMessage("\n".join(problems))
    except AttributeError:
        pass


@transaction.atomic
def get_helmet_timetables():
    """
    Old V2 API makes a return

    :return:None
    """
    url = "https://api.kirjastot.fi/v2/search/libraries?consortium=helmet&with=periods"
    resp = requests.get(url)
    assert resp.status_code == 200
    data = resp.json()  # ??

    # data = [{'id': 'H53', 'periods': []}]

    for unit_data in data:
        try:
            identifier = UnitIdentifier.objects.get(
                namespace='helmet',
                value=unit_data['identificator'])
        except ObjectDoesNotExist:
            continue

        unit = identifier.unit
        with transaction.atomic():
            unit.periods.all().delete()
            print("Processing periods for %s" % unit)
            process_v2_periods(unit, unit_data)
            unit.update_opening_hours()


def process_v2_periods(unit, unit_data):

    for period in unit_data['periods']:

        if not period.get('start', False):
            continue  # NOTE: period is supposed to have *at least* start

        #  start = datetime.datetime.strptime(period['start'], '%Y-%m-%d')

        start = period['start']

        if not period['end']:
            this_day = datetime.date.today()
            end = str(datetime.date(this_day.year + 1, 12, 31))  # No end time goes to end of next year
        else:
            end = period['end']

        active_period = unit.periods.create(
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
                active_period.days.create(
                    weekday=int(day['day']) - 1,
                    opens=opens,
                    closes=closes,
                    closed=day['closed']
                )
            except ValidationError as e:
                print(e)
                print(day)
                raise ValidationError(e)

        # TODO: automagic closing checker
        # One day equals one period and share same closing state
        active_period.closed = period.get('closed')
        active_period.save()


def timetable_fetcher(unit, start='2016-07-01', end='2016-12-31'):
    """
    Fetch periods using kirjastot.fi's new v3 API

    v3 gives opening for each day with period id
    it originated from, thus allowing creation of
    unique periods

    Data is requested first on Unit's kirjastot.fi id,
    then helmet identificator from tprek

    TODO: helmet consortium's id permanency check

    :param unit: Unit object of the library
    :param start: start day for required opening hours
    :param end: end day for required opening hours
    :return: dict|None
    """

    base = "https://api.kirjastot.fi/v3/organisation"

    for identificator in unit.identifiers.all():

        if identificator.namespace == 'kirjastot.fi':
            params = {
                "id": identificator.value,
                "with": "extra,schedules",
                "period.start": start,
                "period.end": end
            }
        elif identificator.namespace == 'helmet':
            params = {
                "identificator": identificator.value,
                "consortium": "2093",  # TODO: Helmet consortium id in v3 API
                "with": "extra,schedules",
                "period.start": start,
                "period.end": end
            }
        else:
            # At this stage no support for other identifier namespaces
            continue

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
    if data['total'] != 1:
        for item in data['items']:
            if item['name']['fi'] == unit.name_fi:
                break
        else:
            raise Exception("No data found for %s" % unit.name_fi)
    else:
        item = data['items'][0]

    for period in item['schedules']:
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

    print("Periods processed for ", unit)
    unit.update_opening_hours()


def get_time_range(start=None, back=1, forward=12):
    """
    From a starting date from back and forward
    by given amount and return start of both months
    as dates

    :param start: datetime.date
    :param back: int
    :param forward: int
    :return: (datetime.date, datetime.date)
    """
    base = delorean.Delorean(start)
    start = base.last_month(back).date.replace(day=1)
    end = base.next_month(forward).date.replace(day=1)
    return start, end
