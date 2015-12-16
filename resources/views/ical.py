from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import renderers
from rest_framework.reverse import reverse
from icalendar import Calendar, Event, vDatetime, vText, vGeo

from resources.models import Reservation, Resource


def build_reservations_ical_file(reservations):
    """
    Return iCalendar file containing given reservations
    """

    cal = Calendar()
    cal['X-WR-CALNAME'] = vText('RESPA')
    cal['name'] = vText('RESPA')
    for reservation in reservations:
        event = Event()
        event['uid'] = 'respa_reservation_{}'.format(reservation.id)
        event['dtstart'] = vDatetime(reservation.begin)
        event['dtend'] = vDatetime(reservation.end)
        unit = reservation.resource.unit
        event['location'] = vText('{} {} {}'.format(unit.name, unit.street_address, unit.address_zip))
        event['geo'] = vGeo(unit.location)
        event['summary'] = vText('{} {}'.format(unit.name, reservation.resource.name))
        cal.add_component(event)
    return cal.to_ical()


def build_ical_feed_url(ical_token, request):
    """
    Return iCal feed url for given token without query parameters
    """

    url = reverse('ical-feed', kwargs={'ical_token': ical_token}, request=request)
    return url[:url.find('?')]


class ICalRenderer(renderers.BaseRenderer):
    media_type = 'text/calendar'
    format = 'ics'

    def render(self, data, media_type=None, renderer_context=None):
        return data.decode(self.charset)


class ICalFeedView(APIView):
    """
    Fetch a user's reservations in iCalendar format
    """

    renderer_classes = (ICalRenderer, )

    def get(self, request, ical_token, format=None):
        User = get_user_model()
        try:
            user = User.objects.get(ical_token=ical_token)
        except User.DoesNotExist:
            raise PermissionDenied
        reservations = Reservation.objects.filter(user=user).active()
        ical_file = build_reservations_ical_file(reservations)
        response = Response(ical_file)
        return response
