from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

User = get_user_model()


class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        (None, {'fields': ('department_name', 'uuid', 'favorite_resources')}),
    )

admin.site.register(User, UserAdmin)
