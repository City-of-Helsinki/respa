from django.contrib.auth import get_user_model
from rest_framework import permissions, serializers, generics, mixins, viewsets

from resources.models.utils import build_ical_feed_url
from resources.models import Unit


all_views = []


def register_view(klass, name, base_name=None):
    entry = {'class': klass, 'name': name}
    if base_name is not None:
        entry['base_name'] = base_name
    all_views.append(entry)


class UserSerializer(serializers.ModelSerializer):
    display_name = serializers.ReadOnlyField(source='get_display_name')
    ical_feed_url = serializers.SerializerMethodField()
    staff_perms = serializers.SerializerMethodField()

    class Meta:
        fields = [
            'last_login', 'username', 'email', 'date_joined',
            'first_name', 'last_name', 'uuid', 'department_name',
            'is_staff', 'display_name', 'ical_feed_url', 'staff_perms', 'favorite_resources'
        ]
        model = get_user_model()

    def get_ical_feed_url(self, obj):
        return build_ical_feed_url(obj.get_or_create_ical_token(), self.context['request'])

    def get_staff_perms(self, obj):
        perm_objs = obj.userobjectpermission_set.all()
        perms = {}
        # We support only units for now
        for p in perm_objs:
            if p.content_type.model_class() != Unit:
                continue
            obj_perms = perms.setdefault(p.object_pk, [])
            perm_name = p.permission.codename
            if perm_name.startswith('unit:'):
                perm_name = perm_name[5:]
            obj_perms.append(perm_name)
        if not perms:
            return {}
        return {'unit': perms}


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
