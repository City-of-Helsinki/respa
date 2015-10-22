import datetime
import pprint

from django.http import HttpResponse

import resources.models
import resources.timetools


def testing_view(request):
    """
    Testing various ways of getting to resources by their availability time
    This function gets you active period for all resources in given date range

    TODO: filter depending on closed state, but this depends on weekday state as well and this needs additional work
    TODO: -> exclude end before my start and start after my end

    :param start_date, end_date:
    :return: most specific Resource
    """
    start_date = request.GET.get('start_date', '2015-03-02')
    end_date = request.GET.get('end_date', '2015-03-07')
    duration = request.GET.get('duration', 2)
    begin = datetime.datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.datetime.strptime(end_date, '%Y-%m-%d')
    duration = datetime.timedelta(hours=duration)
    openings, avail = resources.timetools.get_availability(begin, end, duration=duration)

    return HttpResponse('<html><body>opens<br><pre>' + pprint.pformat(openings.values()) + '</pre> avail<br>' +
                        '<pre>' + pprint.pformat(avail.values()) + '</pre></body></html>')


def tester():

    begin = datetime.datetime(2015, 3, 2)
    end = datetime.datetime(2015, 3, 7)
    begin_utc = resources.timetools.TimeWarp(dt=begin).astimezone('UTC')
    end_utc = resources.timetools.TimeWarp(dt=end).astimezone('UTC')
    duration = datetime.timedelta(hours=2)
    openings, avail = resources.timetools.get_availability(begin_utc, end_utc, duration=duration)

    return openings, avail
