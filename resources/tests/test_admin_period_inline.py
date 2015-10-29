# -*- coding: utf-8 -*-
from datetime import date, time

import pytest
from django.contrib.admin import site as admin_site

from resources.admin.period_inline import PeriodModelForm, prefix_weekday
from resources.models import Period, Resource
from resources.models.unit import Unit
from resources.tests.utils import assert_response_contains, get_form_data


@pytest.mark.django_db
@pytest.mark.parametrize("commit", (False, True))
def test_period_model_form(space_resource, commit):
    period = Period(resource=space_resource, start=date(2015, 8, 1), end=date(2015, 11, 1), name="plop")
    period.full_clean()
    period.save()
    for wd in range(7):
        period.days.create(weekday=wd, opens=time(9, wd * 2), closes=time(12 + wd))

    pmf = PeriodModelForm(instance=period)
    data = get_form_data(pmf, prepared=True)
    # Make every day open at 06, set closed on wednesdays
    for key in list(data.keys()):
        if key.startswith(prefix_weekday(2, "")):
            data[key] = ""
        elif key.endswith("opens"):
            data[key] = "06:00"
    pmf = PeriodModelForm(instance=period, data=data)
    assert pmf.is_valid()
    period = pmf.save(commit=commit)
    if not commit:
        period.save()
        pmf.save_m2m()

    assert all(day.opens.hour == 6 for day in period.days.all())
    assert not period.days.filter(weekday=2).exists()  # Weekdays _got_ closed, yeah?


@pytest.mark.django_db
@pytest.mark.parametrize("model", (Resource, Unit))
def test_period_inline_containing_admins_work(rf, admin_user, model, space_resource, test_unit):
    if model is Resource:
        instance = space_resource
    elif model is Unit:
        instance = test_unit
    else:
        raise NotImplementedError("Unexpected parametrization")

    admin = admin_site._registry[model]  # Sorry for accessing a private member :(
    request = rf.get("/")
    request.user = admin_user
    response = admin.change_view(request, instance.pk)
    assert_response_contains(response, prefix_weekday(2, "opens"))  # should have a weekday field
