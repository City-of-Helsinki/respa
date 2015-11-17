from django.contrib.auth import get_user_model
from rest_framework import permissions, serializers, generics, mixins, viewsets


all_views = []


def register_view(klass, name, base_name=None):
    entry = {'class': klass, 'name': name}
    if base_name is not None:
        entry['base_name'] = base_name
    all_views.append(entry)


class UserSerializer(serializers.ModelSerializer):

    def to_representation(self, obj):
        ret = super(UserSerializer, self).to_representation(obj)
        if obj.first_name and obj.last_name:
            ret['display_name'] = '%s %s' % (obj.first_name, obj.last_name)
        return ret

    class Meta:
        fields = [
            'last_login', 'username', 'email', 'date_joined',
            'first_name', 'last_name', 'uuid', 'department_name',
            'is_staff'
        ]
        model = get_user_model()


class UserViewSet(viewsets.ReadOnlyModelViewSet):

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return self.queryset
        else:
            return self.queryset.filter(pk=user.pk)

    def get_object(self):
        username = self.kwargs.get('username', None)
        if username:
            qs = self.get_queryset()
            obj = generics.get_object_or_404(qs, username=username)
        else:
            obj = self.request.user
        return obj

    permission_classes = [permissions.IsAuthenticated]
    queryset = get_user_model().objects.all()
    serializer_class = UserSerializer

register_view(UserViewSet, 'user')
