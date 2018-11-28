from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import renderers

from resources.models import Reservation
from resources.models.utils import build_reservations_ical_file


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
