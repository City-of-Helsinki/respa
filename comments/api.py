from datetime import datetime
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _
from rest_framework import exceptions, mixins, permissions, serializers, viewsets

from resources.api.base import register_view
from .models import Comment, COMMENTABLE_MODELS


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
        content_type = ContentType.objects.get(model=validated_data.pop('target_type'))
        validated_data['content_type'] = content_type
        return super().create(validated_data)

    def validate(self, validated_data):
        target_type = validated_data.get('target_type')
        if target_type not in COMMENTABLE_MODELS:
            raise exceptions.ValidationError({'target_type': [_('Illegal type.')]})

        target_id = validated_data.get('object_id')
        target_class = ContentType.objects.get(model=target_type).model_class()

        try:
            target_class.objects.get(id=target_id)
        except target_class.DoesNotExist:
            error_message = serializers.PrimaryKeyRelatedField.default_error_messages['does_not_exist']
            raise exceptions.ValidationError(
                {'target_id': [error_message.format(pk_value=target_id)]}
            )
        return validated_data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['target_type'] = instance.content_type.model
        return data


class CommentPermission(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.created_by == request.user


class CommentViewSet(mixins.CreateModelMixin, mixins.RetrieveModelMixin, mixins.ListModelMixin,
                     viewsets.GenericViewSet):
    queryset = Comment.objects.select_related('created_by').prefetch_related('content_type')
    serializer_class = CommentSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, created_at=datetime.now())

register_view(CommentViewSet, 'comment')
