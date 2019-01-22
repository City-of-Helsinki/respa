from datetime import datetime
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
import django_filters
from rest_framework import exceptions, mixins, serializers, viewsets

from resources.api.base import register_view
from .models import Comment, COMMENTABLE_MODELS, get_commentable_content_types


class CommentUserSerializer(serializers.ModelSerializer):
    display_name = serializers.ReadOnlyField(source='get_display_name')

    class Meta:
        model = get_user_model()
        fields = ('display_name',)


class CommentSerializer(serializers.ModelSerializer):
    target_type = serializers.CharField(required=True, write_only=True)  # populated in to_representation()
    target_id = serializers.IntegerField(source='object_id')
    created_by = CommentUserSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ('id', 'created_at', 'created_by', 'target_type', 'target_id', 'text')

    def create(self, validated_data):
        model = COMMENTABLE_MODELS.get(validated_data.pop('target_type'))
        content_type = ContentType.objects.get_for_model(model)
        validated_data['content_type'] = content_type
        return super().create(validated_data)

    def validate(self, validated_data):
        target_type = validated_data.get('target_type')
        if target_type not in COMMENTABLE_MODELS.keys():
            raise exceptions.ValidationError({'target_type': [_('Illegal type.')]})

        target_id = validated_data.get('object_id')
        target_model = COMMENTABLE_MODELS.get(target_type)

        try:
            target_object = target_model.objects.get(id=target_id)
        except target_model.DoesNotExist:
            error_message = serializers.PrimaryKeyRelatedField.default_error_messages['does_not_exist']
            raise exceptions.ValidationError(
                {'target_id': [error_message.format(pk_value=target_id)]}
            )

        if not Comment.can_user_comment_object(self.context['request'].user, target_object):
            raise exceptions.ValidationError(_('You cannot comment this object.'))

        return validated_data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        target_model = instance.content_type.model_class()
        # when used with the comment viewset it shouldn't be possible to get StopIteration here
        # because other than commentable models are excluded in the viewset
        data['target_type'] = next(api_name for api_name, model in COMMENTABLE_MODELS.items() if model == target_model)
        return data


class CommentFilter(django_filters.rest_framework.FilterSet):
    class Meta:
        model = Comment
        fields = ('target_type', 'target_id')

    target_type = django_filters.CharFilter(method='filter_target_type')
    target_id = django_filters.CharFilter(field_name='object_id')

    def filter_target_type(self, queryset, name, value):
        try:
            model = next(model for api_name, model in COMMENTABLE_MODELS.items() if api_name == value)
        except StopIteration:
            return queryset.none()

        content_type = ContentType.objects.get_for_model(model)
        return queryset.filter(content_type=content_type)


class CommentViewSet(mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin,
                     viewsets.GenericViewSet):
    queryset = Comment.objects.select_related('created_by').prefetch_related('content_type')
    serializer_class = CommentSerializer
    filter_backends = (django_filters.rest_framework.DjangoFilterBackend,)
    filterset_class = CommentFilter

    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        return queryset.filter(content_type__in=get_commentable_content_types()).can_view(user)

    def perform_create(self, serializer):
        obj = serializer.save(created_by=self.request.user, created_at=timezone.now())
        obj.send_created_notification(self.request)
        return obj


register_view(CommentViewSet, 'comment')
