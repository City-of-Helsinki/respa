# -*- coding: utf-8 -*-
import pytest

from resources.models import Resource, ResourceImage, ResourceType
from resources.tests.utils import create_resource_image


@pytest.mark.django_db
def test_only_one_main_image(space_resource):
    i1 = create_resource_image(space_resource, type="main")
    assert i1.type == "main"
    i2 = create_resource_image(space_resource, type="main")

    assert i2.type == "main"
    # The first image should have been turned non-main after the new main image was created
    assert ResourceImage.objects.get(pk=i1.pk).type == "other"

    i3 = create_resource_image(space_resource, type="other")
    assert i3.type == "other"
    # But adding a new non-main image should not have dethroned i2 from being main
    assert ResourceImage.objects.get(pk=i2.pk).type == "main"
