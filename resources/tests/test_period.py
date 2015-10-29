# -*- coding: utf-8 -*-
from datetime import date

import pytest

from resources.models import Period


@pytest.mark.django_db
def test_period_can_be_resaved(space_resource):
    period = Period(resource=space_resource, start=date(2015, 8, 1), end=date(2015, 11, 1), name="test")
    period.save()
    period.name += "too"
    period.save()
