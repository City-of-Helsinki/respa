# -*- coding: utf-8 -*-
import pytest

from django.core.urlresolvers import reverse

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
