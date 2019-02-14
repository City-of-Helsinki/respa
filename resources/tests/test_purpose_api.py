# -*- coding: utf-8 -*-
import pytest

from django.urls import reverse

from .utils import check_only_safe_methods_allowed


@pytest.fixture
def list_url():
    return reverse('purpose-list')


@pytest.mark.django_db
@pytest.fixture
def detail_url(purpose):
    purpose.save()
    return reverse('purpose-detail', kwargs={'pk': purpose.pk})


@pytest.mark.django_db
def test_disallowed_methods(all_user_types_api_client, list_url, detail_url):
    """
    Tests that only safe methods are allowed to purpose list and detail endpoints.
    """
    check_only_safe_methods_allowed(all_user_types_api_client, (list_url, detail_url))


@pytest.mark.django_db
def test_non_public_purpose_visibility(api_client, purpose, user, list_url):
    resp = api_client.get(list_url)
    assert resp.status_code == 200
    assert resp.data['count'] == 1

    purpose.public = False
    purpose.save()
    resp = api_client.get(list_url)
    assert resp.status_code == 200
    assert resp.data['count'] == 0

    api_client.force_authenticate(user=user)
    resp = api_client.get(list_url)
    assert resp.status_code == 200
    assert resp.data['count'] == 0

    user.is_general_admin = True
    user.save()
    resp = api_client.get(list_url)
    assert resp.status_code == 200
    assert resp.data['count'] == 1

    user.is_general_admin = False
    user.is_staff = True
    user.save()
    resp = api_client.get(list_url)
    assert resp.status_code == 200
    assert resp.data['count'] == 1
