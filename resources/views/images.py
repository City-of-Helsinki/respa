import os
from mimetypes import guess_type

from django.http.response import FileResponse, HttpResponseBadRequest
from django.views.generic import DetailView
from easy_thumbnails.files import get_thumbnailer

from resources.models import ResourceImage


def parse_dimension_string(dim):
    """
    Parse a dimension string ("WxH") into (width, height).

    :param dim: Dimension string
    :type dim: str
    :return: Dimension tuple
    :rtype: tuple[int, int]
    """
    a = dim.split('x')
    if len(a) != 2:
        raise ValueError('"dim" must be <width>x<height>')
    width, height = a
    try:
        width = int(width)
        height = int(height)
    except:
        width = height = 0
    if not (width > 0 and height > 0):
        raise ValueError("width and height must be positive integers")
    # FIXME: Check allowed image dimensions better
    return (width, height)


class ResourceImageView(DetailView):
    model = ResourceImage

    def get(self, request, *args, **kwargs):
        image = self.get_object()

        dim = request.GET.get('dim', None)
        if dim:
            try:
                width, height = parse_dimension_string(dim)
            except ValueError as verr:
                return HttpResponseBadRequest(str(verr))
        else:
            width = height = None

        if not width:
            out_image = image.image
            filename = image.image.name
        else:
            out_image = get_thumbnailer(image.image).get_thumbnail({
                'size': (width, height),
                'box': image.cropping,
                'crop': True,
                'detail': True,
            })
            filename = "%s-%dx%d%s" % (image.image.name, width, height, os.path.splitext(out_image.name)[1])

        # FIXME: Use SendFile headers instead of Django output when not in debug mode
        out_image.seek(0)
        resp = FileResponse(out_image, content_type=guess_type(filename, False)[0])
        resp["Content-Disposition"] = "attachment; filename=%s" % os.path.basename(filename)
        return resp
