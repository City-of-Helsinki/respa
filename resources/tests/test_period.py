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
        period.clean()
    assert ei.value.code == "no_belonging"

    period.resource = space_resource
    period.unit = test_unit
    with pytest.raises(ValidationError) as ei:
        period.clean()
    assert ei.value.code == "invalid_belonging"


@pytest.mark.skip
@pytest.mark.django_db
@pytest.mark.parametrize("offsets", [
    (-120, -120),  # overlap at the start of the big period
    (+120, +120),  # overlap at the end of the big period
    (+120, -120),  # overlap within the big period
    (-120, +120),  # overlap outside the big period
], ids=["start", "end", "within", "outside"])
def test_period_overlaps(space_resource, offsets):
    big_period = Period.objects.create(
        resource=space_resource, start=date(2015, 1, 1), end=date(2015, 12, 1), name="test"
    )
    start_days, end_days = offsets
    overlap_period = Period(
        resource=space_resource,
        start=big_period.start + timedelta(days=start_days),
        end=big_period.end + timedelta(days=end_days),
        name="overlap"
    )
    with pytest.raises(ValidationError) as ei:
        overlap_period.clean()
    assert ei.value.code == "overlap"


@pytest.mark.skip
@pytest.mark.django_db
def test_multiple_exceptional_periods(space_resource):
    Period.objects.create(
        resource=space_resource, start=date(2015, 1, 1), end=date(2015, 12, 1), name="test"
    )
    Period.objects.create(
        resource=space_resource,
        start=date(2015, 6, 1),
        end=date(2015, 8, 1),
        name="summer",
        exception=True
    )
    with pytest.raises(ValidationError) as ei:
        Period(
            resource=space_resource,
            start=date(2015, 7, 1),
            end=date(2015, 7, 15),
            name="going_fishing",
            exception=True
        ).clean()
    assert ei.value.code == "multiple_exceptions"


@pytest.mark.skip
@pytest.mark.django_db
def test_larger_exceptional_period(space_resource):
    Period.objects.create(
        resource=space_resource, start=date(2015, 1, 1), end=date(2015, 12, 1), name="test"
    )
    with pytest.raises(ValidationError) as ei:
        Period(
            resource=space_resource, start=date(2014, 1, 1), end=date(2016, 12, 1), name="test", exception=True
        ).clean()
    assert ei.value.code == "larger_exception_than_parent"


@pytest.mark.skip
@pytest.mark.django_db
def test_exceptional_period_exceptioning_multiple_periods(space_resource):
    Period.objects.create(resource=space_resource, start=date(2015, 1, 1), end=date(2015, 7, 1), name="test1")
    Period.objects.create(resource=space_resource, start=date(2015, 7, 2), end=date(2015, 12, 1), name="test2")

    with pytest.raises(ValidationError) as ei:
        Period(
            resource=space_resource,
            start=date(2015, 6, 1),
            end=date(2015, 8, 1),
            name="summer",
            exception=True
        ).clean()
    assert ei.value.code == "exception_for_multiple_periods"


@pytest.mark.skip
@pytest.mark.django_db
def test_exceptional_period_without_regular_period(space_resource):
    with pytest.raises(ValidationError) as ei:
        Period(
            resource=space_resource,
            start=date(2015, 6, 1),
            end=date(2015, 8, 1),
            name="summer",
            exception=True
        ).clean()
    assert ei.value.code == "no_regular_period"

@pytest.mark.skip
@pytest.mark.django_db
def test_exceptional_period_with_regular_period(space_resource):
    period = Period(resource=space_resource, start=date(2015, 8, 1), end=date(2015, 11, 1), name="test")
    period.clean()
    period.save()
    exception = Period(
            resource=space_resource,
            start=date(2015, 10, 24),
            end=date(2015, 10, 24),
            name="united_nations_day",
            exception=True
        )
    exception.clean()
    exception.save()
    period.name += "too"
    period.clean()
    period.save()


@pytest.mark.django_db
def test_dayless_period_closed(space_resource):
    period = Period.objects.create(
        resource=space_resource, start=date(2015, 1, 1), end=date(2015, 12, 1), name="test"
    )
    assert period.closed  # No days; is closed
    Day.objects.create(period=period, weekday=0, closed=True)
    period.save_closedness()
    assert period.closed  # Closed day added; not closed
    Day.objects.create(period=period, weekday=1, opens=time(9), closes=time(15))
    period.save_closedness()
    assert not period.closed  # Open day added; not closed
