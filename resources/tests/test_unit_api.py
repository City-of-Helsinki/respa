# -*- coding: utf-8 -*-
import pytest

from resources.models import Equipment, EquipmentAlias, ResourceEquipment
from django.core.urlresolvers import reverse

from .utils import check_only_safe_methods_allowed


@pytest.fixture
def list_url():
    return reverse('equipment-list')


@pytest.mark.django_db
@pytest.fixture
def detail_url(test_unit):
    return reverse('unit-detail', kwargs={'pk': test_unit.pk})


@pytest.mark.django_db
def test_disallowed_methods(staff_api_client, list_url, detail_url):
    """
    Tests that only safe methods are allowed to unit list and detail endpoints.
    """
    check_only_safe_methods_allowed(staff_api_client, (list_url, detail_url))
