import uuid
import django_filters
from datetime import datetime
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError
from rest_framework import viewsets, serializers, filters, exceptions, permissions
from rest_framework.fields import BooleanField

from munigeo import api as munigeo_api
from resources.models import Reservation, Resource

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
        fields = ['url', 'id', 'resource', 'user', 'begin', 'end', 'comments']

    def validate(self, data):
        # if updating a reservation, its identity must be provided to validator
        try:
            reservation = self.context['view'].get_object()
        except AssertionError:
            # the view is a list, which means that we are POSTing a new reservation
            reservation = None
        user = self.context['request'].user

        # Check user specific reservation restrictions relating to given period.
        data['resource'].validate_reservation_period(reservation, user, data=data)

        # Check maximum number of active reservations per user per resource.
        # Only new reservations are taken into account ie. a normal user can modify an existing reservation
        # even if it exceeds the limit. (one that was created via admin ui for example).
        if reservation is None:
            data['resource'].validate_max_reservations_per_user(user)

        if 'comments' in data:
            if not data['resource'].is_admin(user):
                raise ValidationError(dict(comments=_('Only allowed to be set by staff members')))

        # Run model clean
        instance = Reservation(**data)
        instance.clean()

        return data

    def to_representation(self, instance):
        data = super(ReservationSerializer, self).to_representation(instance)
        # Show the comments field only for staff
        if not instance.resource.is_admin(self.context['request'].user):
            del data['comments']
        return data


class UserFilterBackend(filters.BaseFilterBackend):
    """
    Filter that only allows users to see their own objects.
    """
    def filter_queryset(self, request, queryset, view):
        user = request.query_params.get('user', None)
        if not user:
            user = request.user
            if not user.is_authenticated():
                return queryset
            else:
                return queryset.filter(user=user)
        else:
            try:
                user_uuid = uuid.UUID(user)
            except ValueError:
                raise exceptions.ParseError('invalid user UUID value')
            return queryset.filter(user__uuid=user_uuid)


class ActiveFilterBackend(filters.BaseFilterBackend):
    """
    Filter only active reservations.
    """

    def filter_queryset(self, request, queryset, view):
        past = request.query_params.get('all', 'false')
        past = BooleanField().to_internal_value(past)
        if not past:
            now = datetime.now()
            return queryset.filter(end__gte=now)
        return queryset


class ReservationPermission(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user


class ReservationViewSet(munigeo_api.GeoModelAPIView, viewsets.ModelViewSet):
    queryset = Reservation.objects.all()
    serializer_class = ReservationSerializer
    filter_backends = (UserFilterBackend, ActiveFilterBackend)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


register_view(ReservationViewSet, 'reservation')
