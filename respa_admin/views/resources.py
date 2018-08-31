from django.contrib import messages
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse_lazy

from django.views.generic import (
    CreateView,
    ListView,
)

from resources.models import Resource, Period, Day, ResourceImage

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

    def get_success_url(self, **kwargs):
        messages.success(self.request, 'Resurssi tallennettu')
        return reverse_lazy('respa_admin:edit-resource', kwargs={
            'resource_id': self.object.id,
        })

    def get(self, request, *args, **kwargs):
        if kwargs:
            self.object = Resource.objects.get(pk=kwargs['resource_id'])
        else:
            self.object = None

        form_class = self.get_form_class()
        form = self.get_form(form_class)

        period_formset_with_days = get_period_formset(
            self.request,
            instance=self.object,
        )

        resource_image_formset = get_resource_image_formset(
            self.request,
            instance=self.object,
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

        self._delete_extra_periods_days(period_formset_with_days)
        period_formset_with_days.instance = self.object
        period_formset_with_days.save()

        self._save_resource_purposes()
        self._save_resource_images(resource_image_formset)

        return HttpResponseRedirect(self.get_success_url())

    def _save_resource_purposes(self):
        checked_purposes = self.request.POST.getlist('purposes')

        for purpose in checked_purposes:
            self.object.purposes.add(purpose)

    def _save_resource_images(self, resource_image_formset):
        count = len(resource_image_formset)

        for i in range(count):
            resource_image = resource_image_formset.forms[i].save(commit=False)
            resource_image.resource = self.object

            if self.request.FILES:
                resource_image.image = self.request.FILES['images-' + str(i) + '-image']

            resource_image.save()

    def _delete_extra_periods_days(self, period_formset_with_days):
        data = period_formset_with_days.data

        period_ids = get_formset_ids('periods', data)

        if period_ids is None:
            return

        Period.objects.filter(resource=self.object).exclude(pk__in=period_ids).delete()

        period_count = to_int(data.get('periods-TOTAL_FORMS'))

        if not period_count:
            return

        for i in range(period_count):
            period_id = to_int(data.get('periods-{}-id'.format(i)))

            if period_id is None:
                continue

            day_ids = get_formset_ids('days-periods-{}'.format(i), data)
            if day_ids is not None:
                Day.objects.filter(period=period_id).exclude(pk__in=day_ids).delete()

    def forms_invalid(self, form, period_formset_with_days, resource_image_formset):
        return self.render_to_response(
            self.get_context_data(
                form=form,
                period_formset_with_days=period_formset_with_days,
                resource_image_formset=resource_image_formset,
            )
        )


def get_formset_ids(formset_name, data):
    count = to_int(data.get('{}-TOTAL_FORMS'.format(formset_name)))
    if count is None:
        return None

    ids_or_nones = (
        to_int(data.get('{}-{}-{}'.format(formset_name, i, 'id')))
        for i in range(count)
    )

    return {x for x in ids_or_nones if x is not None}


def to_int(string):
    if not string or not string.isdigit():
        return None
    return int(string)
