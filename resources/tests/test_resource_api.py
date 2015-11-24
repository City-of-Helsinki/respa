import pytest
from django.core.urlresolvers import reverse


def _check_permissions_dict(api_client, resource, is_admin, can_make_reservation):
    """
    Check that user permissions returned from resource endpoint contain correct values
    for given user and resource. api_client should have the user authenticated.
    """

    url = reverse('resource-detail', kwargs={'pk': resource.pk})
    response = api_client.get(url)
    assert response.status_code == 200
    permissions = response.data['user_permissions']
    assert len(permissions) == 2
    assert permissions['is_admin'] == is_admin
    assert permissions['can_make_reservations'] == can_make_reservation


@pytest.mark.django_db
def test_user_permissions_in_resource_endpoint(api_client, resource_in_unit, user):
    """
    Tests that resource endpoint returns a permissions dict with correct values.
    """
    api_client.force_authenticate(user=user)

    # normal user reservable True, expect is_admin False can_make_reservations True
    _check_permissions_dict(api_client, resource_in_unit, False, True)

    # normal user reservable False, expect is_admin False can_make_reservations False
    resource_in_unit.reservable = False
    resource_in_unit.save()
    _check_permissions_dict(api_client, resource_in_unit, False, False)

    # staff member reservable False, expect is_admin True can_make_reservations True
    user.is_staff = True
    user.save()
    api_client.force_authenticate(user=user)
    _check_permissions_dict(api_client, resource_in_unit, True, True)
