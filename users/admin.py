from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib import admin

User = get_user_model()


def _add_general_admin_to_fieldsets(fieldsets):
    def modify_field_data(field_data):
        if 'is_superuser' in (field_data or {}).get('fields', ()):
            fields = list(field_data['fields'])
            fields.insert(fields.index('is_superuser'), 'is_general_admin')
            return dict(field_data, fields=tuple(fields))
        return field_data

    return tuple(
        (label, modify_field_data(field_data))
        for (label, field_data) in fieldsets)


class UserAdmin(DjangoUserAdmin):
    fieldsets = _add_general_admin_to_fieldsets(DjangoUserAdmin.fieldsets) + (
        (None, {'fields': ('department_name', 'uuid', 'favorite_resources')}),
    )
    list_display = [
        'uuid', 'username', 'email',
        'first_name', 'last_name',
        'is_staff', 'is_general_admin', 'is_superuser'
    ]
    list_filter = [
        'is_staff', 'is_general_admin', 'is_superuser',
        'is_active',
        'groups',
    ]


admin.site.register(User, UserAdmin)
