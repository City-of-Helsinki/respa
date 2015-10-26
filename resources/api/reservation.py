from rest_framework import viewsets

from munigeo import api as munigeo_api
from resources.models import Reservation

from .base import NullableDateTimeField, TranslatedModelSerializer, register_view


class ReservationSerializer(TranslatedModelSerializer, munigeo_api.GeoModelSerializer):
    begin = NullableDateTimeField()
    end = NullableDateTimeField()

    class Meta:
        model = Reservation
        fields = ['url', 'resource', 'user', 'begin', 'end']

    def validate(self, data):
        # if updating a reservation, its identity must be provided to validator
        try:
            reservation = self.context['view'].get_object()
        except AssertionError:
            # the view is a list, which means that we are POSTing a new reservation
            reservation = None
        data['begin'], data['end'] = data['resource'].get_reservation_period(reservation, data=data)
        return data


class ReservationViewSet(munigeo_api.GeoModelAPIView, viewsets.ModelViewSet):
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer

register_view(ReservationViewSet, 'reservation')
