from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest
from django.conf import settings
from django.views.generic import View
from django.shortcuts import get_object_or_404
from easy_thumbnails.files import get_thumbnailer

from .models import ResourceImage


class ResourceImageView(View):
    def get(self, request, pk, ext):
        if ext != 'jpg':
            # FIXME
            return HttpResponseBadRequest('only JPEG images supported')
        image = get_object_or_404(ResourceImage, pk=pk)

        dim = request.GET.get('dim', None)
        if dim:
            a = dim.split('x')
            if len(a) != 2:
                return HttpResponseBadRequest('"dim" must be <width>x<height>')
            width, height = a
            try:
                width = int(width)
                height = int(height)
            except:
                width = height = 0
            if not width or not height:
                return HttpResponseBadRequest("width and height must be positive integers")
            # FIXME: Check allowed image dimensions
        else:
            width = height = None

        if not width:
            url = image.image.url
        else:
            url = get_thumbnailer(image.image).get_thumbnail({
                'size': (width, height),
                'box': image.cropping,
                'crop': True,
                'detail': True,
            }).url

        # FIXME: Use SendFile headers instead of redirect when not in debug
        # mode
        return HttpResponseRedirect(redirect_to=url)
