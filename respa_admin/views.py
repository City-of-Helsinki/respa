from django.template.response import TemplateResponse
from django.views.generic.list import ListView

from resources.models import Resource




def admin_index(request):
    return TemplateResponse(request, 'index.html')


class ResourceListView(ListView):
    model = Resource
    context_object_name = 'resources'
