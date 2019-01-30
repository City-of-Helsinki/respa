from django.contrib.auth import get_user_model
from rest_framework import viewsets, serializers, filters, exceptions, permissions, status, pagination, generics
from rest_framework.response import Response
from users.api import UserSerializer as RespaUserSerializer
from users.models import User
from resources.api.base import TranslatedModelSerializer, register_view

class StaffWriteOnly(permissions.BasePermission):
     def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS or request.user.is_staff

class UserSerializer(RespaUserSerializer):
    display_name = serializers.ReadOnlyField(source='get_display_name')
    ical_feed_url = serializers.SerializerMethodField()
    staff_perms = serializers.SerializerMethodField()

    class Meta:
        fields = [
            'last_login', 'username', 'email', 'date_joined',
            'first_name', 'last_name', 'uuid', 'department_name',
            'is_staff', 'is_superuser', 'display_name', 'staff_perms', 'favorite_resources'
        ]
        model = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [StaffWriteOnly]
    serializer_class = UserSerializer

    def get_object(self):
        pk = self.kwargs.get('pk')
        if pk == "current" and not self.request.user.is_anonymous():
            return self.request.user
        else:
            return None
        return super(UserViewSet, self).get_object()

register_view(UserViewSet, 'user', base_name='user')
