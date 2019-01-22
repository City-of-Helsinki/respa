# -*- coding: utf-8 -*-
import pytest
from django.urls import reverse
from django.utils.six import BytesIO
from PIL import Image

from resources.tests.utils import create_resource_image
from resources.views.images import parse_dimension_string


@pytest.mark.django_db
def test_resource_image_view(client, space_resource):
    jpeg = create_resource_image(space_resource, size=(300, 300), format="JPEG")
    png = create_resource_image(space_resource, size=(300, 300), format="PNG")
    assert png.image_format == "PNG"
    resp = client.get(reverse("resource-image-view", kwargs={"pk": jpeg.pk}))
    assert resp["Content-Type"] == "image/jpeg"
    resp = client.get(reverse("resource-image-view", kwargs={"pk": png.pk}))
    assert resp["Content-Type"] == "image/png"


@pytest.mark.django_db
def test_resource_image_view_thumbing(client, space_resource):
    png = create_resource_image(space_resource, size=(300, 300), format="PNG")
    resp = client.get(reverse("resource-image-view", kwargs={"pk": png.pk}), data={"dim": "50x50"})
    assert resp["Content-Type"] == "image/jpeg"  # Thumbnails should be PNG even if source data isn't
    img_data = resp.getvalue()
    assert Image.open(BytesIO(img_data)).size == (50, 50)

    # Rudimentary checking of invalid `dim`s -- better testing in `test_dimension_string_parsing`
    assert client.get(reverse("resource-image-view", kwargs={"pk": png.pk}), data={"dim": "-x3"}).status_code == 400


def test_dimension_string_parsing():
    with pytest.raises(ValueError):
        parse_dimension_string("3x8x2")

    with pytest.raises(ValueError):
        parse_dimension_string("0x-1")

    with pytest.raises(ValueError):
        parse_dimension_string("x")

    assert parse_dimension_string("100x100") == (100, 100)
