from rest_framework import serializers
from resources.models import Reservation, Resource
from resources.models.reservation import RESERVATION_EXTRA_FIELDS
from resources.api.reservation import ReservationSerializer
from resources.api.base import TranslatedModelSerializer
from hmlvaraus.api.resource import ResourceSerializer

from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError
from django.utils import timezone

class ReservationSerializer(ReservationSerializer):

    reserver_name = serializers.CharField(required=True)

    class Meta:
        model = Reservation
        fields = ['url', 'id', 'resource', 'user', 'begin', 'end', 'comments', 'is_own', 'state',
                  'need_manual_confirmation', 'staff_event', 'access_code'] + list(RESERVATION_EXTRA_FIELDS)

    # def validate(self, data):
    #     return data

    def validate(self, data):
        reservation = self.instance
        request_user = self.context['request'].user

        # this check is probably only needed for PATCH
        try:
            resource = data['resource']
        except KeyError:
            resource = reservation.resource

        if not resource.can_make_reservations(request_user):
            raise PermissionDenied()

        if data['end'] < timezone.now():
            raise ValidationError(_('You cannot make a reservation in the past'))

        if not resource.is_admin(request_user):
            reservable_before = resource.get_reservable_before()
            if reservable_before and data['begin'] >= reservable_before:
                raise ValidationError(_('The resource is reservable only before %(datetime)s' %
                                        {'datetime': reservable_before}))

        # normal users cannot make reservations for other people
        if not resource.is_admin(request_user):
            data.pop('user', None)

        if 'comments' in data:
            if not resource.is_admin(request_user):
                raise ValidationError(dict(comments=_('Only allowed to be set by staff members')))

        if 'access_code' in data:
            if data['access_code'] == None:
                data['access_code'] = ''

            access_code_enabled = resource.is_access_code_enabled()

            if not access_code_enabled and data['access_code']:
                raise ValidationError(dict(access_code=_('This field cannot have a value with this resource')))

            if access_code_enabled and reservation and data['access_code'] != reservation.access_code:
                raise ValidationError(dict(access_code=_('This field cannot be changed')))

        # Mark begin of a critical section. Subsequent calls with this same resource will block here until the first
        # request is finished. This is needed so that the validations and possible reservation saving are
        # executed in one block and concurrent requests cannot be validated incorrectly.
        Resource.objects.select_for_update().get(pk=resource.pk)

        # Check maximum number of active reservations per user per resource.
        # Only new reservations are taken into account ie. a normal user can modify an existing reservation
        # even if it exceeds the limit. (one that was created via admin ui for example).
        if reservation is None:
            resource.validate_max_reservations_per_user(request_user)
            return data # FIXME Prevents "Run model clean". For some reason this validation can't get self.instance.

        # Run model clean
        data.pop('staff_event', None)
        instance = Reservation(**data)
        try:
            instance.clean(original_reservation=reservation)
        except DjangoValidationError as exc:

            # Convert Django ValidationError to DRF ValidationError so that in the response
            # field specific error messages are added in the field instead of in non_field_messages.
            if not hasattr(exc, 'error_dict'):
                raise ValidationError(exc)
            error_dict = {}
            for key, value in exc.error_dict.items():
                error_dict[key] = [error.message for error in value]
            raise ValidationError(error_dict)

        return data

    def to_representation(self, instance):
        data = super(TranslatedModelSerializer, self).to_representation(instance)
        resource = instance.resource
        user = self.context['request'].user

        # Show the comments field and the user object only for staff
        if not resource.is_admin(user):
            del data['comments']
            del data['user']

        return data

    def validate_reserver_name(self, value):
        if not value :
            raise serializers.ValidationError("Reserver name is required")
        return value