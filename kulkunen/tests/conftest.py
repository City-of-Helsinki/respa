import pytest
from django.utils.module_loading import import_string

from kulkunen import models as kulkunen_models
from kulkunen.models import AccessControlResource, AccessControlSystem
from resources.tests.conftest import *  # noqa


@pytest.fixture
def test_driver(monkeypatch):
    for drv in kulkunen_models.DRIVERS:
        if drv[0] == 'test':
            break
    else:
        drivers = kulkunen_models.DRIVERS + (('test', 'Test driver', 'kulkunen.tests.driver.TestDriver'),)
        monkeypatch.setattr(kulkunen_models, 'DRIVERS', drivers)
        drv = drivers[-1]

    return import_string(drv[2])


@pytest.fixture
def ac_system(test_driver):
    return AccessControlSystem.objects.create(
        name='test acs',
        driver='test',
    )


@pytest.fixture
def ac_resource(ac_system, resource_in_unit):
    return AccessControlResource.objects.create(
        system=ac_system, resource=resource_in_unit
    )
