from django.contrib.auth import get_user_model
from rest_framework import viewsets, serializers

from munigeo import api as munigeo_api
from resources.models import Reservation

from .base import NullableDateTimeField, TranslatedModelSerializer, register_view

# FIXME: Make this configurable?
USER_ID_ATTRIBUTE = 'id'
try:
    get_user_model()._meta.get_field_by_name('uuid')
    USER_ID_ATTRIBUTE = 'uuid'
except:
    pass


class ReservationSerializer(TranslatedModelSerializer, munigeo_api.GeoModelSerializer):
    begin = NullableDateTimeField()
    end = NullableDateTimeField()
    user = serializers.ReadOnlyField(source='user.' + USER_ID_ATTRIBUTE)

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

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

register_view(ReservationViewSet, 'reservation')
