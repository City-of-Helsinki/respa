import pytest

from django.contrib.auth.models import AnonymousUser

from resources.enums import UnitAuthorizationLevel, UnitGroupAuthorizationLevel
from resources.models import Resource, ResourceType, Unit
from users.models import User

from respa_admin import permissions as perm


@pytest.mark.django_db
@pytest.mark.parametrize('permission_func,scope,role_allowances', [
    # The "role_allowances" string contains following letter codes
    # either in upper case or lower case.  Upper case means allowed and
    # lower case means denied.
    #
    # Super User
    # |   General Administrator
    # |  |  Unit Group Administrator
    # |  |  |   Unit Administrator
    # |  |  |   |  Unit Manager
    # |  |  |   |  |  Normal logged in user
    # |  |  |   |  |  | Anonymous, non logged in user
    # |  |  |   |  |  | |
    # SU GA UGA UA UM N A
    (perm.can_login_to_respa_admin, 'general',
     'SU GA UGA UA UM n a'),
    (perm.can_modify_resource, 'resource',
     'SU GA UGA UA UM n a'),
    (perm.can_modify_unit, 'unit',
     'SU GA UGA UA UM n a'),
    (perm.can_access_permissions_view, 'general',
     'SU GA UGA UA um n a'),
    (perm.can_search_users, 'general',
     'SU GA UGA UA um n a'),
    (perm.can_manage_resource_perms, 'resource',
     'SU GA UGA UA um n a'),
    (perm.can_manage_auth_of_unit, 'unit',
     'SU GA UGA UA um n a'),
    (perm.can_create_resource_to_unit, 'unit',
     'SU GA UGA UA um n a'),
    (perm.can_delete_resource_of_unit, 'unit',
     'SU GA UGA UA um n a'),
    (perm.can_manage_auth_of_unit_group, 'unit group',
     'SU GA UGA ua um n a'),
    (perm.can_create_unit_to_group, 'unit group',
     'SU GA UGA ua um n a'),
    (perm.can_delete_unit_of_group, 'unit group',
     'SU GA UGA ua um n a'),
])
def test_permissions(permission_func, scope, role_allowances):
    resource = get_resource('A')
    unit = resource.unit
    unit_group = resource.unit.unit_groups.first()

    other_resource = get_resource('B')
    other_unit = other_resource.unit

    inside_users = {
        role: get_user(role, unit)
        for role in role_allowances.upper().split()
    }
    outside_users = {
        role: get_user(role, other_unit)
        for role in role_allowances.upper().split()
    }

    for role_allowance in role_allowances.split():
        role = role_allowance.upper()
        allowed_by_table = (role == role_allowance)
        inside_user = inside_users[role]
        outside_user = outside_users[role]

        for (user, is_insider) in [(inside_user, True), (outside_user, False)]:
            allowed_by_scope = (
                True if (role in {'SU', 'GA'} or scope == 'general')
                else is_insider)
            allowed = (allowed_by_scope and allowed_by_table)

            if scope == 'general':
                result = permission_func(user)
            elif scope == 'resource':
                result = permission_func(user, resource)
            elif scope == 'unit':
                result = permission_func(user, unit)
            elif scope == 'unit group':
                result = permission_func(user, unit_group)
            else:  # pragma: no cover
                raise ValueError("Unknown scope: {}".format(scope))

            assert result == allowed, (
                "Role {r} {p} as {i} should be {exp} but it is {actl}".format(
                    r=role, p=permission_func.__name__,
                    i=('insider' if is_insider else 'outsider'),
                    exp=allowed, actl=result))


@pytest.mark.django_db
def test_can_modify_resource_matches_queryset():
    res_x = get_resource('X')
    res_y = get_resource('Y')
    res_z = get_resource('Z')

    user_su = get_user('SU')
    user_ga = get_user('GA')
    user_um_x = get_user('UM', res_x.unit)
    user_um_x_y = get_user('UM', res_x.unit, res_y.unit)
    user_um_z = get_user('UM', res_z.unit)
    user_norm = get_user('N')
    user_anon = get_user('A')

    access_matrix = [
        (user_su, [res_x, res_y, res_z]),
        (user_ga, [res_x, res_y, res_z]),
        (user_um_x, [res_x]),
        (user_um_x_y, [res_x, res_y]),
        (user_um_z, [res_z]),
        (user_norm, []),
        (user_anon, []),
    ]

    for (user, resources) in access_matrix:
        modifiable_by = Resource.objects.modifiable_by(user)
        for resource in modifiable_by:
            assert perm.can_modify_resource(user, resource)
        for resource in Resource.objects.exclude(pk__in=modifiable_by):
            assert not perm.can_modify_resource(user, resource)
        assert {x.pk for x in modifiable_by} == {x.pk for x in resources}


def get_resource(name):
    resource_type = ResourceType.objects.get_or_create(
        main_type='space', name='space')[0]
    unit = Unit.objects.create(name='unit-{}'.format(name))
    unit.unit_groups.create(name='ug-{}'.format(name))
    resource = Resource.objects.create(
        unit=unit,
        type=resource_type,
        name='res-{}'.format(name),
        authentication='none')
    return resource


def get_user(role, *units):
    units_str = '_'.join(unit.name.lower() for unit in units)
    username = '{}-{}'.format(role.lower(), units_str)
    user = User.objects.create_user(
        username=username, password='password',
        first_name=role, last_name=units_str)

    if role == 'SU':
        user.is_superuser = True
        user.save()
    elif role == 'GA':
        user.is_staff = True
        user.is_general_admin = True
        user.save()
    elif role == 'UGA':
        user.is_staff = True
        for unit in units:
            user.unit_group_authorizations.create(
                subject=unit.unit_groups.first(),
                level=UnitGroupAuthorizationLevel.admin,
                authorized=user)
    elif role == 'UA':
        user.is_staff = True
        for unit in units:
            user.unit_authorizations.create(
                subject=unit,
                level=UnitAuthorizationLevel.admin,
                authorized=user)
    elif role == 'UM':
        user.is_staff = True
        for unit in units:
            user.unit_authorizations.create(
                subject=unit,
                level=UnitAuthorizationLevel.manager,
                authorized=user)
    elif role == 'N':
        pass
    elif role == 'A':
        user = AnonymousUser()
    else:  # pragma: no cover
        raise ValueError("Unknown role: {}".format(role))

    return user
