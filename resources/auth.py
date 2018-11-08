def is_authenticated_user(user):
    return bool(user and user.is_authenticated)


def is_staff(user):
    return is_authenticated_user(user) and (
        user.is_staff or user.is_superuser or is_any_admin(user))


def is_general_admin(user):
    return is_authenticated_user(user) and (
        user.is_superuser or getattr(user, 'is_general_admin', False))


def is_any_admin(user):
    return is_authenticated_user(user) and (
        is_general_admin(user) or
        user.unit_group_authorizations.admin_level().exists() or
        user.unit_authorizations.admin_level().exists())
