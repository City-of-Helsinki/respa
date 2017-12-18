import uuid
import arrow
import django_filters
from datetime import datetime
from arrow.parser import ParserError
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, serializers, filters, exceptions, permissions
from rest_framework.authentication import TokenAuthentication
from rest_framework.fields import BooleanField, IntegerField
from rest_framework import renderers
from rest_framework.exceptions import NotAcceptable, ValidationError
from guardian.shortcuts import get_objects_for_user

from helusers.jwt import JWTAuthentication
from munigeo import api as munigeo_api
from resources.models import Reservation, Resource, Unit
from resources.models.reservation import RESERVATION_EXTRA_FIELDS
from resources.pagination import ReservationPagination
from users.models import User
from resources.models.utils import generate_reservation_xlsx, get_object_or_none

from .base import NullableDateTimeField, TranslatedModelSerializer, register_view

# FIXME: Make this configurable?
USER_ID_ATTRIBUTE = 'id'
try:
    get_user_model()._meta.get_field('uuid')
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
    is_own = serializers.SerializerMethodField()
    state = serializers.ChoiceField(choices=Reservation.STATE_CHOICES, required=False)
    need_manual_confirmation = serializers.ReadOnlyField()
    staff_event = serializers.BooleanField(required=False, write_only=True)

    class Meta:
        model = Reservation
        fields = ['url', 'id', 'resource', 'user', 'begin', 'end', 'comments', 'is_own', 'state',
                  'need_manual_confirmation', 'staff_event', 'access_code'] + list(RESERVATION_EXTRA_FIELDS)
        read_only_fields = RESERVATION_EXTRA_FIELDS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        data = self.get_initial()
        resource = None

        # try to find out the related resource using initial data if that is given
        resource_id = data.get('resource') if data else None
        if resource_id:
            resource = get_object_or_none(Resource, id=resource_id)

        # if that didn't work out use the reservation's old resource if such exists
        if not resource:
            if isinstance(self.instance, Reservation) and isinstance(self.instance.resource, Resource):
                resource = self.instance.resource

        # set supported and required extra fields
        if resource:
            supported = resource.get_supported_reservation_extra_field_names()
            required = resource.get_required_reservation_extra_field_names()

            if resource.need_manual_confirmation:

                # manually confirmed reservations have some extra conditions
                can_approve = resource.can_approve_reservations(self.context['request'].user)
                if data.get('staff_event', False) and can_approve:
                    required = {'reserver_name', 'event_description'}

            # we don't need to remove a field here if it isn't supported, as it will be read-only and will be more
            # easily removed in to_representation()
            for field_name in supported:
                self.fields[field_name].read_only = False

            for field_name in required:
                self.fields[field_name].required = True

    def validate_state(self, value):
        instance = self.instance
        request_user = self.context['request'].user

        # new reservations will get their value regardless of this value
        if not instance:
            return value

        # state not changed
        if instance.state == value:
            return value

        if instance.resource.can_approve_reservations(request_user):
            allowed_states = (Reservation.REQUESTED, Reservation.CONFIRMED, Reservation.DENIED)
            if instance.state in allowed_states and value in allowed_states:
                return value

        raise ValidationError(_('Illegal state change'))

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

        # Check user specific reservation restrictions relating to given period.
        resource.validate_reservation_period(reservation, request_user, data=data)

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

    def to_internal_value(self, data):
        user_data = data.pop('user', None)  # handle user manually
        deserialized_data = super().to_internal_value(data)

        # validate user and convert it to User object
        if user_data:
            UserSerializer(data=user_data).is_valid(raise_exception=True)
            try:
                deserialized_data['user'] = User.objects.get(**{USER_ID_ATTRIBUTE: user_data['id']})
            except User.DoesNotExist:
                raise ValidationError({
                    'user': {
                        'id': [_('Invalid pk "{pk_value}" - object does not exist.').format(pk_value=user_data['id'])]
                    }
                })
        return deserialized_data

    def to_representation(self, instance):
        data = super(ReservationSerializer, self).to_representation(instance)
        resource = instance.resource
        user = self.context['request'].user

        if self.context['request'].accepted_renderer.format == 'xlsx':
            # Return somewhat different data in case we are dealing with xlsx.
            # The excel renderer needs datetime objects, so begin and end are passed as objects
            # to avoid needing to convert them back and forth.
            data.update(**{
                'unit': resource.unit.name,  # additional
                'resource': resource.name,  # resource name instead of id
                'begin': instance.begin,  # datetime object
                'end': instance.end,  # datetime object
                'user': instance.user.email,  # just email
                'created_at': instance.created_at
            })

        # Show the comments field and the user object only for staff
        if not resource.is_admin(user):
            del data['comments']
            del data['user']

        if instance.are_extra_fields_visible(user):
            supported_fields = set(resource.get_supported_reservation_extra_field_names())
        else:
            supported_fields = set()

        for field_name in RESERVATION_EXTRA_FIELDS:
            if field_name not in supported_fields:
                data.pop(field_name, None)

        if not (resource.is_access_code_enabled() and instance.can_view_access_code(user)):
            data.pop('access_code')

        if 'access_code' in data and data['access_code'] == '':
            data['access_code'] = None

        return data

    def get_is_own(self, obj):
        return obj.user == self.context['request'].user


class UserFilterBackend(filters.BaseFilterBackend):
    """
    Filter by user uuid and by is_own.
    """
    def filter_queryset(self, request, queryset, view):
        user = request.query_params.get('user', None)
        if user:
            try:
                user_uuid = uuid.UUID(user)
            except ValueError:
                raise exceptions.ParseError(_('Invalid value in filter %(filter)s') % {'filter': 'user'})
            queryset = queryset.filter(user__uuid=user_uuid)

        if not request.user.is_authenticated():
            return queryset

        is_own = request.query_params.get('is_own', None)
        if is_own is not None:
            is_own = is_own.lower()
            if is_own in ('true', 't', 'yes', 'y', '1'):
                queryset = queryset.filter(user=request.user)
            elif is_own in ('false', 'f', 'no', 'n', '0'):
                queryset = queryset.exclude(user=request.user)
            else:
                raise exceptions.ParseError(_('Invalid value in filter %(filter)s') % {'filter': 'is_own'})
        return queryset


class ExcludePastFilterBackend(filters.BaseFilterBackend):
    """
    Exclude reservations in the past.
    """

    def filter_queryset(self, request, queryset, view):
        past = request.query_params.get('all', 'false')
        past = BooleanField().to_internal_value(past)
        if not past:
            now = datetime.now()
            return queryset.filter(end__gte=now)
        return queryset


class ResourceFilterBackend(filters.BaseFilterBackend):
    """
    Filter reservations by resource.
    """

    def filter_queryset(self, request, queryset, view):
        resource = request.query_params.get('resource', None)
        if resource:
            return queryset.filter(resource__id=resource)
        return queryset


class ReservationFilterBackend(filters.BaseFilterBackend):
    """
    Filter reservations by time.
    """

    def filter_queryset(self, request, queryset, view):
        params = request.query_params
        times = {}
        past = False
        for name in ('start', 'end'):
            if name not in params:
                continue
            # whenever date filtering is in use, include past reservations
            past = True
            try:
                times[name] = arrow.get(params[name]).to('utc').datetime
            except ParserError:
                raise exceptions.ParseError("'%s' must be a timestamp in ISO 8601 format" % name)
        is_detail_request = 'pk' in request.parser_context['kwargs']
        if not past and not is_detail_request:
            past = params.get('all', 'false')
            past = BooleanField().to_internal_value(past)
            if not past:
                now = datetime.now()
                queryset = queryset.filter(end__gte=now)
        if times.get('start', None):
            queryset = queryset.filter(end__gte=times['start'])
        if times.get('end', None):
            queryset = queryset.filter(begin__lte=times['end'])
        return queryset


class NeedManualConfirmationFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        filter_value = request.query_params.get('need_manual_confirmation', None)
        if filter_value is not None:
            need_manual_confirmation = BooleanField().to_internal_value(filter_value)
            return queryset.filter(resource__need_manual_confirmation=need_manual_confirmation)
        return queryset


class StateFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        state = request.query_params.get('state', None)
        if state:
            queryset = queryset.filter(state__in=state.replace(' ', '').split(','))
        return queryset


class CanApproveFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        filter_value = request.query_params.get('can_approve', None)
        if filter_value:
            queryset = queryset.filter(resource__need_manual_confirmation=True)
            units = get_objects_for_user(user=request.user, perms=['can_approve_reservation'], klass=Unit)
            can_approve = BooleanField().to_internal_value(filter_value)
            if can_approve:
                queryset = queryset.filter(resource__unit__in=units)
            else:
                queryset = queryset.exclude(resource__unit__in=units)
        return queryset


class ReservationPermission(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        # reservations that need manual confirmation and are confirmed cannot be
        # modified or cancelled without reservation approve permission
        cannot_approve = not obj.resource.can_approve_reservations(request.user)
        if obj.need_manual_confirmation() and obj.state == Reservation.CONFIRMED and cannot_approve:
            return False

        return obj.resource.is_admin(request.user) or obj.user == request.user


class ReservationExcelRenderer(renderers.BaseRenderer):
    media_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    format = 'xlsx'
    charset = None
    render_style = 'binary'

    def render(self, data, media_type=None, renderer_context=None):
        if not renderer_context or renderer_context['response'].status_code == 404:
            return bytes()
        if renderer_context['view'].action == 'retrieve':
            return generate_reservation_xlsx([data])
        elif renderer_context['view'].action == 'list':
            return generate_reservation_xlsx(data['results'])
        else:
            return NotAcceptable()


class ReservationViewSet(munigeo_api.GeoModelAPIView, viewsets.ModelViewSet):
    queryset = Reservation.objects.select_related('user', 'resource', 'resource__unit')

    serializer_class = ReservationSerializer
    filter_backends = (filters.OrderingFilter, UserFilterBackend, ResourceFilterBackend, ReservationFilterBackend,
                       NeedManualConfirmationFilterBackend, StateFilterBackend, CanApproveFilterBackend)
    permission_classes = (permissions.IsAuthenticatedOrReadOnly, ReservationPermission)
    renderer_classes = (renderers.JSONRenderer, renderers.BrowsableAPIRenderer, ReservationExcelRenderer)
    pagination_class = ReservationPagination
    #authentication_classes = (JWTAuthentication, TokenAuthentication)
    ordering_fields = ('begin',)

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        # staff members can see all reservations
        if user.is_staff:
            return queryset

        # normal users can see only their own reservations and reservations that are confirmed or requested
        filters = Q(state__in=(Reservation.CONFIRMED, Reservation.REQUESTED))
        if user.is_authenticated():
            filters |= Q(user=user)

        queryset = queryset.filter(filters)
        return queryset

    def perform_create(self, serializer):
        kwargs = {'created_by': self.request.user, 'modified_by': self.request.user}
        if 'user' not in serializer.validated_data:
            kwargs['user'] = self.request.user

        resource = serializer.validated_data['resource']
        staff_event = (self.request.data.get('staff_event', False) and
                       resource.can_approve_reservations(self.request.user))
        if resource.need_manual_confirmation and not staff_event:
            kwargs['state'] = Reservation.REQUESTED
        else:
            kwargs['state'] = Reservation.CONFIRMED

        instance = serializer.save(**kwargs)

        if instance.state == Reservation.REQUESTED:
            instance.send_reservation_requested_mail()
            instance.send_reservation_requested_mail_to_officials()
        elif instance.state == Reservation.CONFIRMED and resource.is_access_code_enabled():
            instance.send_reservation_created_with_access_code_mail()

    def perform_update(self, serializer):
        old_instance = self.get_object()
        new_state = serializer.validated_data.pop('state', old_instance.state)
        new_instance = serializer.save(modified_by=self.request.user)
        new_instance.set_state(new_state, self.request.user)

    def perform_destroy(self, instance):
        instance.set_state(Reservation.CANCELLED, self.request.user)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        if request.accepted_renderer.format == 'xlsx':
            response['Content-Disposition'] = 'attachment; filename={}.xlsx'.format(_('reservations'))
        return response

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        if request.accepted_renderer.format == 'xlsx':
            response['Content-Disposition'] = 'attachment; filename={}-{}.xlsx'.format(_('reservation'), kwargs['pk'])
        return response

register_view(ReservationViewSet, 'reservation')

