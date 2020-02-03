from .enums import UnitGroupAuthorizationLevel, UnitAuthorizationLevel

def is_authenticated_user(user):
    return bool(user and user.is_authenticated)


def is_superuser(user):
    return is_authenticated_user(user) and user.is_superuser


def is_general_admin(user):
    return is_authenticated_user(user) and (
        user.is_superuser or getattr(user, 'is_general_admin', False))


def is_staff(user):
    return is_authenticated_user(user) and user.is_staff


def is_any_admin(user):
    if not is_authenticated_user(user):
        return False

    group_authorizations = user.unit_group_authorizations.all()
    authorizations = user.unit_authorizations.all()

    is_unit_group_admin = any(group_auth.level == UnitGroupAuthorizationLevel.admin for group_auth in group_authorizations)
    is_unit_admin = any(auth.level == UnitAuthorizationLevel.admin for auth in authorizations)

    return is_general_admin(user) or is_unit_group_admin or is_unit_admin


def is_unit_admin(unit_authorizations, unit_group_authorizations, unit):
    is_admin = False

    for group_auth in filter(lambda group_auth: group_auth.level == UnitGroupAuthorizationLevel.admin, unit_group_authorizations):
        if any(member_unit == unit for member_unit in group_auth.subject.members.all()):
            is_admin = True

    if any(auth.subject == unit and auth.level == UnitAuthorizationLevel.admin for auth in unit_authorizations):
        is_admin = True

    return is_admin


def is_unit_manager(unit_authorizations, unit):
    return any(auth.subject == unit and auth.level == UnitAuthorizationLevel.manager for auth in unit_authorizations)


def is_unit_viewer(unit_authorizations, unit):
    return any(auth.subject == unit and auth.level == UnitAuthorizationLevel.viewer for auth in unit_authorizations)
