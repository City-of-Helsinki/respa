# -*- coding: utf-8 -*-


from django.core.files.base import ContentFile
from django.test.testcases import SimpleTestCase
from django.utils.six import BytesIO
from PIL import Image

from resources.models import ResourceImage


def get_test_image_data(size=(32, 32), color=(250, 250, 210), format="JPEG"):
    """
    Get binary image data with the given specs.

    :param size: Size tuple
    :type size: tuple[int, int]
    :param color: RGB color triple
    :type color: tuple[int, int, int]
    :param format: PIL image format specifier
    :type format: str
    :return: Binary data
    :rtype: bytes
    """
    img = Image.new(mode="RGB", size=size)
    img.paste(color)
    sio = BytesIO()
    img.save(sio, format=format, quality=75)
    return sio.getvalue()


def create_resource_image(resource, size=(32, 32), color=(250, 250, 210), format="JPEG", **instance_kwargs):
    """
    Create a ResourceImage object with image data with the given specs.

    :param resource: Resource to attach the ResourceImage to.
    :type resource: resources.models.Resource
    :param size: Size tuple
    :type size: tuple[int, int]
    :param color: RGB color triple
    :type color: tuple[int, int, int]
    :param format: PIL image format specifier
    :type format: str
    :param instance_kwargs: Other kwargs for `ResourceImage`. Some values are sanely prefilled.
    :type instance_kwargs: dict
    :return: Saved ResourceImage
    :rtype: resources.models.ResourceImage
    """
    instance_kwargs.setdefault("sort_order", resource.images.count() + 1)
    instance_kwargs.setdefault("type", "main")
    instance_kwargs.setdefault("image", ContentFile(
        get_test_image_data(size=size, color=color, format=format),
        name="%s.%s" % (instance_kwargs["sort_order"], format.lower())
    ))
    ri = ResourceImage(resource=resource, **instance_kwargs)
    ri.full_clean()
    ri.save()
    return ri


_dummy_test_case = SimpleTestCase()


def assert_response_contains(response, text, **kwargs):
    _dummy_test_case.assertContains(response=response, text=text, **kwargs)


def assert_response_does_not_contain(response, text, **kwargs):
    _dummy_test_case.assertNotContains(response=response, text=text, **kwargs)
