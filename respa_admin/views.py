from django.template.response import TemplateResponse
from django.views.generic.list import ListView

from resources.models import Resource

def admin_index(request):
    return TemplateResponse(request, 'index.html')

def admin_office(request):
    return TemplateResponse(request, 'page_office.html')


def admin_form(request):
    return TemplateResponse(request, 'page_form.html')

class ResourceListView(ListView):
    model = Resource
    paginate_by = 10
    context_object_name = 'resources'
    template_name = 'page_resources.html'
