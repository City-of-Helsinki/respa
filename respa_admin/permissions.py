from resources.auth import is_any_admin, is_staff

########################################################################
# General permissions


def can_login_to_respa_admin(user):
    return is_staff(user)


def can_access_permissions_view(user):
    return is_any_admin(user)


def can_search_users(user):
    return is_any_admin(user)


########################################################################
# Resource permissions


def can_modify_resource(user, resource):
    return resource.unit.is_manager(user)


def can_manage_resource_perms(user, resource):
    return resource.unit.is_admin(user)


########################################################################
# Unit permissions


def can_modify_unit(user, unit):
    return unit.is_manager(user)


def can_manage_auth_of_unit(user, unit):
    return unit.is_admin(user)


def can_create_resource_to_unit(user, unit):
    return unit.is_admin(user)


def can_delete_resource_of_unit(user, unit):
    return unit.is_admin(user)


########################################################################
# Unit Group permissions


def can_manage_auth_of_unit_group(user, unit_group):
    return unit_group.is_admin(user)


def can_create_unit_to_group(user, unit_group):
    return unit_group.is_admin(user)


def can_delete_unit_of_group(user, unit_group):
    return unit_group.is_admin(user)
