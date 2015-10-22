# -*- coding: utf-8 -*-


from django.core.files.base import ContentFile
from django.utils.six import BytesIO
from PIL import Image

from resources.models import ResourceImage


def get_test_image_data(size=(32, 32), color=(250, 250, 210)):
    img = Image.new(mode="RGB", size=size)
    img.paste(color)
    sio = BytesIO()
    img.save(sio, format="JPEG", quality=75)
    return sio.getvalue()


def create_resource_image(resource, **kwargs):
    kwargs.setdefault("image_format", "JPEG")
    kwargs.setdefault("sort_order", resource.images.count() + 1)
    kwargs.setdefault("type", "main")
    kwargs.setdefault("image", ContentFile(get_test_image_data(), name="%s.jpg" % kwargs["sort_order"]))
    ri = ResourceImage(resource=resource, **kwargs)
    ri.full_clean()
    ri.save()
    return ri
