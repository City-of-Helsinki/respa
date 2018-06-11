from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse

from django.views.generic import (
    CreateView,
    ListView,
)

from resources.models import Resource

from respa_admin.forms import (
    get_period_formset,
    get_resource_image_formset,
    ResourceForm,
)


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


class SaveResourceView(CreateView):
    """
    View for saving new resources and updating existing resources.
    """

    http_method_names = ['get', 'post']
    success_url = 'success'  # This is just for testing purposes.
    model = Resource
    form_class = ResourceForm
    template_name = 'resources/create_resource.html'
    extra_formsets = 1

    def get(self, request, *args, **kwargs):
        if kwargs:
            self.object = Resource.objects.get(pk=kwargs['resource_id'])
            self.extra_formsets = 0
        else:
            self.object = None

        form_class = self.get_form_class()
        form = self.get_form(form_class)

        period_formset_with_days = get_period_formset(
            self.request,
            extra=self.extra_formsets,
            instance=self.object
        )

        resource_image_formset = get_resource_image_formset(
            self.request,
            extra=self.extra_formsets,
            instance=self.object
        )

        return self.render_to_response(
            self.get_context_data(
                form=form,
                period_formset_with_days=period_formset_with_days,
                resource_image_formset=resource_image_formset,
            )
        )

    def post(self, request, *args, **kwargs):
        if kwargs:
            self.object = Resource.objects.get(pk=kwargs['resource_id'])
        else:
            self.object = None

        form_class = self.get_form_class()
        form = self.get_form(form_class)

        period_formset_with_days = get_period_formset(request=request, instance=self.object)
        resource_image_formset = get_resource_image_formset(request=request, instance=self.object)

        if form.is_valid() and period_formset_with_days.is_valid() and resource_image_formset.is_valid():
            return self.forms_valid(form, period_formset_with_days, resource_image_formset)
        else:
            return self.forms_invalid(form, period_formset_with_days, resource_image_formset)

    def forms_valid(self, form, period_formset_with_days, resource_image_formset):
        self.object = form.save()

        period_formset_with_days.instance = self.object
        period_formset_with_days.save()
        image_count = 0

        checked_purposes = self.request.POST.getlist('purposes')

        for purpose in checked_purposes:
            self.object.purposes.add(purpose)

        if self.request.FILES:
            for form in resource_image_formset:
                resource_image = form.save(commit=False)
                resource_image.resource = self.object
                resource_image.image = self.request.FILES['images-' + str(image_count) + '-image']
                image_count += 1
                resource_image.save()

        return HttpResponseRedirect(self.get_success_url())

    def forms_invalid(self, form, period_formset_with_days, resource_image_formset):
        return self.render_to_response(
            self.get_context_data(
                form=form,
                period_formset_with_days=period_formset_with_days,
                resource_image_formset=resource_image_formset
            )
        )
