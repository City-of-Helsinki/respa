# -*- coding: utf-8 -*-
import pytest

from resources.models import ResourceType
from django.core.urlresolvers import reverse

from .utils import check_only_safe_methods_allowed


@pytest.fixture
def list_url():
    return reverse('resourcetype-list')


@pytest.mark.django_db
@pytest.fixture
def detail_url(space_resource):
    return reverse('resourcetype-detail', kwargs={'pk': space_resource.pk})


@pytest.mark.django_db
def test_disallowed_methods(all_user_types_api_client, list_url, detail_url):
    """
    Tests that only safe methods are allowed to resource type list and detail endpoints.
    """
    check_only_safe_methods_allowed(all_user_types_api_client, (list_url, detail_url))
