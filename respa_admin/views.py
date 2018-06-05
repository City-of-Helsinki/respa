from django.template.response import TemplateResponse
from django.views.generic.list import ListView

from resources.models import Resource

def admin_index(request):
    return TemplateResponse(request, 'index.html')

def admin_office(request):
    return TemplateResponse(request, 'page_office.html')

def admin_resource(request):
    return TemplateResponse(request, 'page_resource.html')

def admin_form(request):
    return TemplateResponse(request, 'page_form.html')

class ResourceListView(ListView):
    model = Resource
    context_object_name = 'resources'
