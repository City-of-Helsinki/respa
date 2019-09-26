import datetime
import delorean
import requests
from django.conf import settings
from django.db import transaction
from sentry_sdk import capture_message
from resources.models import Unit
from typing import Dict, List
from .base import Importer, register_importer

IMPORTER_NAME = "kirjastot"

CLOSED_HOURS = 0
STAFFED_HOURS = 1
SELF_SERVICE_HOURS = 2

KIRKANTA_NAMESPACE = 'kirkanta'
REQUESTS_TIMEOUT = 10


@register_importer
class KirjastotImporter(Importer):
    name = IMPORTER_NAME

    def import_units(self):
        process_varaamo_libraries()


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
    varaamo_units = Unit.objects.filter(identifiers__namespace=KIRKANTA_NAMESPACE)

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
                import traceback
                print("Problem in processing data of library ", varaamo_unit, traceback.format_exc())
                problems.append(" ".join(["Problem in processing data of library ", str(varaamo_unit), str(e)]))
            if varaamo_unit.data_source_hours != IMPORTER_NAME:
                varaamo_unit.data_source_hours = IMPORTER_NAME
                varaamo_unit.save()
        else:
            print("Failed data fetch on library: ", varaamo_unit)
            problems.append(" ".join(["Failed data fetch on library: ", str(varaamo_unit)]))

    try:
        if problems:
            # without Sentry, this will gracefully file the message to /dev/null
            capture_message("\n".join(problems))
    except AttributeError:
        pass


def timetable_fetcher(unit, start='2016-07-01', end='2016-12-31'):
    """
    Fetch periods using kirjastot.fi's v4 API

    v4 gives opening for each day with period id
    it originated from, thus allowing creation of
    unique periods

    :param unit: Unit object of the library
    :param start: start day for required opening hours
    :param end: end day for required opening hours
    :return: dict|None
    """

    base_url = "https://api.kirjastot.fi/v4/library"
    supported_namespaces = (KIRKANTA_NAMESPACE,)

    for identificator in unit.identifiers.all():

        if identificator.namespace not in supported_namespaces:
            continue

        params = {
            "with": "schedules",
            "period.start": start,
            "period.end": end
        }
        url = "{}/{}".format(base_url, identificator.value)
        try:
            response = requests.get(url, params=params, timeout=REQUESTS_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            if data["total"] > 0:
                return data["data"]
            else:
                # There's possibly other identificators that might work
                continue
        except requests.exceptions.RequestException:
            continue

    # No timetables were found :(
    return False


def process_periods(library, unit):
    """
    Generate Period and Day objects into
    given Unit from kirjastot.fi v4 API data

    Each day in data has its own Period and Day object
    resulting in as many Periods with one Day as there is
    items in data

    :param data: kirjastot.fi v4 API data form /library endpoint
    :param unit: Unit
    :return: None
    """
    schedule_days = [parse_schedule(schedule_item) for schedule_item in library['schedules']]

    for day in schedule_days:
        # this is a hack and a workaround - libraries can have many sets of opening hours,
        # such as 09:00-12:00 and 13:00-17:00, during the same day.
        # currently respa can handle only one opening time and one closing time during the
        # same day, so the earliest opening time and latest closing time are selected
        staffed_opening_hours = merge_opening_hours(day['staffed_opening_hours'])
        # missing opening hours are not allowed on open day
        if staffed_opening_hours['from'] is None or staffed_opening_hours['to'] is None:
            day_closed = True
        else:
            day_closed = day['closed']

        period = unit.periods.create(
            start=day['date'],
            end=day['date'],
            description=day['info'],
            closed=day_closed,
            name=day['date'].isoformat()
        )

        period.days.create(weekday=day['weekday'],
                           opens=staffed_opening_hours['from'],
                           closes=staffed_opening_hours['to'],
                           closed=day_closed)

    print("Periods processed for", unit)
    unit.update_opening_hours()


def parse_schedule(day_schedule: Dict[str, any]) -> Dict[str, any]:
    date = datetime.datetime.strptime(day_schedule.get('date'), '%Y-%m-%d').date()
    closed = day_schedule.get('closed', False)
    info = day_schedule.get('info', '')
    # only normal staffed opening hours synced for now.
    # support for staffless and during day closed hours to be added.
    staffed_opening_hours = [hours for hours in day_schedule.get('times', []) if hours['status'] == STAFFED_HOURS]
    return {
        'date': date,
        'weekday': date.weekday(),
        'closed': closed,
        'info': info,
        'staffed_opening_hours': staffed_opening_hours,
    }


def merge_opening_hours(opening_hours: List) -> Dict[str, datetime.time]:
    """ A workaround helper that combines a list of opening times to a single
    pair with the earliest opening and the latest closing time. """
    opening_times = [parse_time(times['from']) for times in opening_hours]
    closing_times = [parse_time(times['to']) for times in opening_hours]
    return {
        'from': min(opening_times) if opening_times else None,
        'to': max(closing_times) if closing_times else None,
    }


def parse_time(time: str) -> datetime.time:
    hour, minute = [int(num) for num in time.split(':')]
    return datetime.time(hour=hour, minute=minute)


def get_time_range(start=None, back: int = 1, forward: int = 12):
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
