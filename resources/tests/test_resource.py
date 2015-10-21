# -*- coding: utf-8 -*-

from django.core.files.base import ContentFile
from django.test import TestCase
import random
from resources.models import Resource, ResourceImage, ResourceType
from resources.tests.utils import get_test_image_data


def create_image(resource, **kwargs):
    kwargs.setdefault("image_format", "JPEG")
    kwargs.setdefault("sort_order", resource.images.count() + 1)
    kwargs.setdefault("type", "main")
    kwargs.setdefault("image", ContentFile(get_test_image_data(), name="%s.jpg" % kwargs["sort_order"]))
    ri = ResourceImage(resource=resource, **kwargs)
    ri.full_clean()
    ri.save()
    return ri


class ResourceImageTestCase(TestCase):
    def test_only_one_main_image(self):
        restype = ResourceType.objects.create()
        res = Resource.objects.create(type=restype, authentication="none", name="resource")
        i1 = create_image(res, type="main")
        assert i1.type == "main"
        i2 = create_image(res, type="main")

        assert i2.type == "main"
        # The first image should have been turned non-main after the new main image was created
        assert ResourceImage.objects.get(pk=i1.pk).type == "other"

        i3 = create_image(res, type="other")
        assert i3.type == "other"
        # But adding a new non-main image should not have dethroned i2 from being main
        assert ResourceImage.objects.get(pk=i2.pk).type == "main"
