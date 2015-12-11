# -*- coding: utf-8 -*-
import pytest

from django.core.urlresolvers import reverse

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
