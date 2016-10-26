# -*- coding: utf-8 -*-
import datetime
import pytest

from django.core.urlresolvers import reverse
from django.utils import timezone
from freezegun import freeze_time

from .utils import check_only_safe_methods_allowed


@pytest.fixture
def list_url():
    return reverse('equipment-list')


@pytest.mark.django_db
@pytest.fixture
def detail_url(test_unit):
    return reverse('unit-detail', kwargs={'pk': test_unit.pk})


@pytest.mark.django_db
def test_disallowed_methods(all_user_types_api_client, list_url, detail_url):
    """
    Tests that only safe methods are allowed to unit list and detail endpoints.
    """
    check_only_safe_methods_allowed(all_user_types_api_client, (list_url, detail_url))


@freeze_time('2016-10-25')
@pytest.mark.django_db
def test_reservable_in_advance_fields(api_client, test_unit, detail_url):
    response = api_client.get(detail_url)
    assert response.status_code == 200

    assert response.data['reservable_days_in_advance'] is None
    assert response.data['reservable_before'] is None

    test_unit.reservable_days_in_advance = 5
    test_unit.save()

    response = api_client.get(detail_url)
    assert response.status_code == 200

    assert response.data['reservable_days_in_advance'] == 5
    before = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=6)
    assert response.data['reservable_before'] == before
