from django.contrib import messages
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse_lazy

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


class ResourceListView(ListView):
    model = Resource
    paginate_by = 10
    context_object_name = 'resources'
    template_name = 'page_resources.html'

    def get_queryset(self):
        qs = super(ResourceListView, self).get_queryset()
        query = self.request.GET.get('q')
        print(bool(query))
        if query:
            qs = qs.filter(name__icontains=query)
        return qs


class RespaAdminIndex(ResourceListView):
    paginate_by = 7
    template_name = 'index.html'


def admin_office(request):
    return TemplateResponse(request, 'page_office.html')


class SaveResourceView(CreateView):
    """
    View for saving new resources and updating existing resources.
    """

    http_method_names = ['get', 'post']
    model = Resource
    form_class = ResourceForm
    template_name = 'resources/create_resource.html'
    extra_formsets = 1

    def get_success_url(self, **kwargs):
        messages.success(self.request, 'Resurssi tallennettu')
        return reverse_lazy('respa_admin:edit-resource', kwargs={
            'resource_id': self.object.id,
        })

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

        if self._validate_forms(form, period_formset_with_days, resource_image_formset):
            return self.forms_valid(form, period_formset_with_days, resource_image_formset)
        else:
            messages.error(request, 'Tallennus epäonnistui. Tarkista lomakkeen virheet.')
            return self.forms_invalid(form, period_formset_with_days, resource_image_formset)

    def _validate_forms(self, form, period_formset, image_formset):
        valid_form = form.is_valid()
        valid_period_form = period_formset.is_valid()
        valid_image_formset = image_formset.is_valid()

        return valid_form and valid_period_form and valid_image_formset

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
                resource_image_formset=resource_image_formset,
            )
        )
