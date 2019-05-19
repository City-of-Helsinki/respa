# -*- coding: utf-8 -*-
import pytest

from django.urls import reverse
from guardian.shortcuts import assign_perm

from .utils import check_only_safe_methods_allowed


@pytest.fixture
def list_url():
    return reverse('user-list')


@pytest.mark.django_db
@pytest.fixture
def detail_url(user):
    return reverse('user-detail', kwargs={'pk': user.pk})


@pytest.mark.django_db
def test_disallowed_methods(all_user_types_api_client, list_url, detail_url):
    """
    Tests that only safe methods are allowed to user list and detail endpoints.
    """
    check_only_safe_methods_allowed(all_user_types_api_client, (list_url, detail_url))


@pytest.mark.django_db
def test_user_perms(api_client, list_url, staff_user, user, test_unit):
    api_client.force_authenticate(user=user)
    response = api_client.get(list_url)
    assert response.status_code == 200
    assert response.data['count'] == 1
    user_data = response.data['results'][0]
    assert not user_data['staff_perms']

    api_client.force_authenticate(user=staff_user)
    response = api_client.get(list_url)
    assert response.status_code == 200
    assert response.data['count'] == 1
    user_data = response.data['results'][0]
    assert not user_data['staff_perms']

    assign_perm('unit:can_approve_reservation', staff_user, test_unit)
    response = api_client.get(list_url)
    assert response.status_code == 200
    assert response.data['count'] == 1
    user_data = response.data['results'][0]
    perms = user_data['staff_perms']
    assert list(perms.keys()) == ['unit']
    perms = perms['unit']
    assert list(perms.items()) == [(test_unit.id, ['can_approve_reservation'])]
