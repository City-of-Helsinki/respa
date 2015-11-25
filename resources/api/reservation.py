import uuid
import django_filters
from datetime import datetime
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError
from rest_framework import viewsets, serializers, filters, exceptions, permissions
from rest_framework.fields import BooleanField, IntegerField

from munigeo import api as munigeo_api
from resources.models import Reservation, Resource
from users.models import User

from .base import NullableDateTimeField, TranslatedModelSerializer, register_view

# FIXME: Make this configurable?
USER_ID_ATTRIBUTE = 'id'
try:
    get_user_model()._meta.get_field_by_name('uuid')
    USER_ID_ATTRIBUTE = 'uuid'
except:
    pass


class UserSerializer(TranslatedModelSerializer):
    display_name = serializers.ReadOnlyField(source='get_display_name')
    email = serializers.ReadOnlyField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if USER_ID_ATTRIBUTE == 'id':
            # id field is read_only by default, that needs to be changed
            # so that the field will be validated
            self.fields['id'] = IntegerField(label='ID')
        else:
            # if the user id attribute isn't id, modify the id field to point to the right attribute.
            # the field needs to be of the right type so that validation works correctly
            model_field_type = type(get_user_model()._meta.get_field(USER_ID_ATTRIBUTE))
            serializer_field = self.serializer_field_mapping[model_field_type]
            self.fields['id'] = serializer_field(source=USER_ID_ATTRIBUTE, label='ID')

    class Meta:
        model = get_user_model()
        fields = ('id', 'display_name', 'email')


class ReservationSerializer(TranslatedModelSerializer, munigeo_api.GeoModelSerializer):
    begin = NullableDateTimeField()
    end = NullableDateTimeField()
    user = UserSerializer(required=False)

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

        # If a user is given in the request convert it to a User object.
        # Its data is already validated by UserSerializer.
        # Currently the user will be changed to the request user when saving,
        # but that will change in the near future.
        if 'user' in data and type(data['user'] != User):
            id = data['user'][USER_ID_ATTRIBUTE]
            try:
                user = User.objects.get(**{USER_ID_ATTRIBUTE: id})
            except User.DoesNotExist:
                raise serializers.ValidationError({
                    'user': {
                        'id': [_('Object with {slug_name}={value} does not exist.').format(slug_name='id', value=id),]
                    }
                })
            data['user'] = user

        # Run model clean
        instance = Reservation(**data)
        instance.clean(original_reservation=reservation)

        return data

    def to_representation(self, instance):
        data = super(ReservationSerializer, self).to_representation(instance)
        # Show the comments field and the user object only for staff
        if not instance.resource.is_admin(self.context['request'].user):
            del data['comments']
            del data['user']
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
