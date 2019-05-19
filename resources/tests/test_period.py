# -*- coding: utf-8 -*-
from datetime import date, timedelta, time
import pytest

from django.core.exceptions import ValidationError
from resources.models import Period, Day


@pytest.mark.django_db
def test_period_can_be_resaved(space_resource):
    period = Period(resource=space_resource, start=date(2015, 8, 1), end=date(2015, 11, 1), name="test")
    period.save()
    period.name += "too"
    period.save()


@pytest.mark.django_db
def test_invalid_date_range(space_resource):
    period = Period(resource=space_resource, start=date(2016, 8, 1), end=date(2015, 11, 1), name="test")
    with pytest.raises(ValidationError) as ei:
        period.clean()
    assert ei.value.code == "invalid_date_range"


@pytest.mark.django_db
def test_invalid_belongings(space_resource, test_unit):
    period = Period(start=date(2015, 8, 1), end=date(2015, 11, 1), name="test")
    with pytest.raises(ValidationError) as ei:
        period._validate_belonging()
    assert ei.value.code == "no_belonging"

    period.resource = space_resource
    period.unit = test_unit
    with pytest.raises(ValidationError) as ei:
        period._validate_belonging()
    assert ei.value.code == "invalid_belonging"


@pytest.mark.django_db
def test_invalid_save_period():
    period = Period(resource=None, start=date(2015, 8, 1), end=date(2015, 11, 1), name="test")
    with pytest.raises(ValidationError) as ei:
        period.save()
    assert ei.value.code == "no_belonging"


@pytest.mark.django_db
def test_none_start_end_time(space_resource):
    period = Period(resource=space_resource, start=None, end=None, name="test")
    with pytest.raises(ValidationError) as ei:
        period.clean()
    assert ei.value.code == "empty_start_end"
