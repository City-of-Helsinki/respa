def is_authenticated_user(user):
    return bool(user and user.is_authenticated)


def is_staff(user):
    return is_authenticated_user(user) and (
        user.is_staff or user.is_superuser or is_general_admin(user))


def is_general_admin(user):
    return is_authenticated_user(user) and (
        user.is_superuser or getattr(user, 'is_general_admin', False))
