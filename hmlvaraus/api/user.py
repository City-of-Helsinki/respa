from rest_framework import viewsets, serializers, filters, exceptions, permissions, status, pagination, generics
from rest_framework.response import Response
from users.api import UserSerializer
from users.models import User
from resources.api.base import TranslatedModelSerializer, register_view

class StaffWriteOnly(permissions.BasePermission):
     def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS or request.user.is_staff

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
