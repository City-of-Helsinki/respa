# -*- coding: utf-8 -*-
import pytest
from django.core.files.base import ContentFile
from PIL import Image
from resources.errors import InvalidImage

from resources.models import ResourceImage
from resources.tests.utils import create_resource_image, get_test_image_data


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


@pytest.mark.django_db
@pytest.mark.parametrize("format", ("BMP", "PCX"))
@pytest.mark.parametrize("image_type", ("main", "map", "ground_plan"))
def test_image_transcoding(space_resource, format, image_type):
    """
    Test that images get transcoded into JPEG or PNG if they're not JPEG/PNG
    """
    data = get_test_image_data(format=format)
    ri = ResourceImage(
        resource=space_resource,
        sort_order=8,
        type=image_type,
        image=ContentFile(data, name="long_horse.%s" % format)
    )
    expected_format = ("PNG" if image_type in ("map", "ground_plan") else "JPEG")
    ri.full_clean()
    assert ri.image_format == expected_format  # Transcoding occurred
    assert Image.open(ri.image).format == expected_format  # .. it really did!


@pytest.mark.django_db
@pytest.mark.parametrize("format", ("JPEG", "PNG"))
def test_image_transcoding_bypass(space_resource, format):
    """
    Test that JPEGs and PNGs bypass transcoding
    """
    data = get_test_image_data(format=format)
    ri = ResourceImage(
        resource=space_resource,
        sort_order=8,
        type="main",
        image=ContentFile(data, name="nice.%s" % format)
    )
    ri.full_clean()
    assert ri.image_format == format  # Transcoding did not occur
    assert Image.open(ri.image).format == format  # no, no transcoding
    ri.image.seek(0)  # PIL may have `seek`ed or read the stream
    assert ri.image.read() == data  # the bitstream is identical


@pytest.mark.django_db
def test_invalid_image(space_resource):
    data = b"this is text, not an image!"
    ri = ResourceImage(
        resource=space_resource,
        sort_order=8,
        type="main",
        image=ContentFile(data, name="bogus.xyz")
    )
    with pytest.raises(InvalidImage) as ei:
        ri.full_clean()
    assert "cannot identify" in ei.value.message
