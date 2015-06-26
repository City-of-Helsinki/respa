from django.shortcuts import render
from .models import Resource, Day
import django.db.models as dbm

# Create your views here.


def testink(start_date, end_date):
    """
    Testing various ways of getting to resources by their availability time
    This function gets you active period for all resources in given date range

    TODO: filter depending on closed state, but this depends on weekday state as well and this needs additional work
    TODO: -> exclude end before my start and start after my end

    :param start_date, end_date:
    :return: most specific Resource
    """

    Day.objects.filter(weekday__in=(1,2), closed=False)

    res = Resource.objects.filter(
        periods__start__lte=start_date, periods__end__gte=end_date).annotate(
        periods_length=dbm.F('periods__end')-dbm.F('periods__start')
    ).order_by('periods_length').distinct()
    return res
