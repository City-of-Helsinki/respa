# -*- coding: utf-8 -*-


from PIL import Image

from django.utils.six import BytesIO


def get_test_image_data(size=(32, 32), color=(250, 250, 210)):
    img = Image.new(mode="RGB", size=size)
    img.paste(color)
    sio = BytesIO()
    img.save(sio, format="JPEG", quality=75)
    return sio.getvalue()
