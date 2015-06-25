from django.shortcuts import render
from .models import Resource
import django.db.models as dbm

# Create your views here.


def testink(start_date, end_date):
    """
    Testing various ways of getting to resources by their availability time
    This function gets you active period for all resources in given date range

    TODO: filter depending on closed state, but this depends on weekday state as well and this needs additional work

    :param start_date, end_date:
    :return: most specific Resource
    """
    res = Resource.objects.filter(
        periods__start__lte=start_date, periods__end__gte=end_date).annotate(
        periods_length=dbm.F('periods__end')-dbm.F('periods__start')
    ).order_by('periods_length').first()
    return res
