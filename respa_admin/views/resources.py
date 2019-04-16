from django.conf import settings
from django.contrib import messages
from django.db.models import FieldDoesNotExist
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView
from django.utils.translation import ugettext_lazy as _
from respa_admin.views.base import ExtraContextMixin

from resources.models import (
    Resource,
    Period,
    Day,
    ResourceImage,
    ResourceType,
    Unit,
)
from respa_admin import forms

from respa_admin.forms import (
    get_period_formset,
    get_resource_image_formset,
    ResourceForm,
)

from respa_admin import accessibility_api


class ResourceListView(ExtraContextMixin, ListView):
    model = Resource
    paginate_by = 10
    context_object_name = 'resources'
    template_name = 'respa_admin/page_resources.html'

    def get(self, request, *args, **kwargs):
        get_params = request.GET
        self.search_query = get_params.get('search_query')
        self.resource_type = get_params.get('resource_type')
        self.resource_unit = get_params.get('resource_unit')
        self.order_by = get_params.get('order_by')
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ResourceListView, self).get_context_data()
        resources = self.get_unfiltered_queryset()
        context['types'] = ResourceType.objects.filter(
            pk__in=resources.values('type'))
        context['units'] = Unit.objects.filter(
            pk__in=resources.values('unit'))
        context['search_query'] = self.search_query
        context['selected_resource_type'] = self.resource_type or ''
        context['selected_resource_unit'] = self.resource_unit or ''
        context['order_by'] = self.order_by or ''
        return context

    def get_unfiltered_queryset(self):
        qs = super(ResourceListView, self).get_queryset()
        qs = qs.modifiable_by(self.request.user)
        return qs

    def get_queryset(self):
        qs = self.get_unfiltered_queryset()

        if self.search_query:
            qs = qs.filter(name__icontains=self.search_query)
        if self.resource_type:
            qs = qs.filter(type=self.resource_type)
        if self.resource_unit:
            qs = qs.filter(unit=self.resource_unit)
        if self.order_by:
            order_by_param = self.order_by.strip('-')
            try:
                if Resource._meta.get_field(order_by_param):
                    qs = qs.order_by(self.order_by)
            except FieldDoesNotExist:
                qs = self.get_unfiltered_queryset()

        qs = qs.prefetch_related('images', 'unit')

        return qs


class RespaAdminIndex(ResourceListView):
    paginate_by = 7
    template_name = 'respa_admin/index.html'


def admin_office(request):
    return TemplateResponse(request, 'respa_admin/page_office.html')


class SaveResourceView(ExtraContextMixin, CreateView):
    """
    View for saving new resources and updating existing resources.
    """
    http_method_names = ['get', 'post']
    model = Resource
    pk_url_kwarg = 'resource_id'
    form_class = ResourceForm
    template_name = 'respa_admin/resources/create_resource.html'

    def get_context_data(self, **kwargs):
        context = super(SaveResourceView, self).get_context_data(**kwargs)
        if settings.RESPA_ADMIN_VIEW_RESOURCE_URL and self.object.id:
            context['RESPA_ADMIN_VIEW_RESOURCE_URL'] = settings.RESPA_ADMIN_VIEW_RESOURCE_URL + self.object.id
        else:
            context['RESPA_ADMIN_VIEW_RESOURCE_URL'] = ''
        return context

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.modifiable_by(self.request.user)

    def get_success_url(self, **kwargs):
        messages.success(self.request, 'Resurssi tallennettu')
        return reverse_lazy('respa_admin:edit-resource', kwargs={
            self.pk_url_kwarg: self.object.id,
        })

    def get(self, request, *args, **kwargs):
        if self.pk_url_kwarg in kwargs:
            self.object = self.get_object()
            page_headline = _('Edit resource')
        else:
            page_headline = _('Create new resource')
            self.object = None

        form = self.get_form()

        period_formset_with_days = get_period_formset(
            self.request,
            instance=self.object,
        )

        resource_image_formset = get_resource_image_formset(
            self.request,
            instance=self.object,
        )

        trans_fields = forms.get_translated_field_count(resource_image_formset)

        accessibility_data_link = self._get_accessibility_data_link(request)

        return self.render_to_response(
            self.get_context_data(
                accessibility_data_link=accessibility_data_link,
                form=form,
                period_formset_with_days=period_formset_with_days,
                resource_image_formset=resource_image_formset,
                trans_fields=trans_fields,
                page_headline=page_headline,
            )
        )

    def _get_accessibility_data_link(self, request):
        if self.object is None or self.object.unit is None or not self.object.unit.is_admin(request.user):
            return None
        if self.object.type.id not in getattr(settings, 'RESPA_ADMIN_ACCESSIBILITY_VISIBILITY', []):
            return None
        if not getattr(settings, 'RESPA_ADMIN_ACCESSIBILITY_API_SECRET', None):
            return None
        api_url = getattr(settings, 'RESPA_ADMIN_ACCESSIBILITY_API_BASE_URL', '')
        system_id = getattr(settings, 'RESPA_ADMIN_ACCESSIBILITY_API_SYSTEM_ID', '')
        secret = getattr(settings, 'RESPA_ADMIN_ACCESSIBILITY_API_SECRET', '')
        target_id = self.object.pk
        target_name = self.object.name
        user = request.user.email or request.user.username
        return accessibility_api.generate_url(
            api_url,
            system_id,
            target_id,
            target_name,
            user,
            secret,
        )

    def post(self, request, *args, **kwargs):
        if self.pk_url_kwarg in kwargs:
            self.object = self.get_object()
        else:
            self.object = None

        form = self.get_form()

        period_formset_with_days = get_period_formset(request=request, instance=self.object)
        resource_image_formset = get_resource_image_formset(request=request, instance=self.object)

        if self._validate_forms(form, period_formset_with_days, resource_image_formset):
            return self.forms_valid(form, period_formset_with_days, resource_image_formset)
        else:
            return self.forms_invalid(form, period_formset_with_days, resource_image_formset)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        unit_field = form.fields['unit']
        unit_field.queryset = unit_field.queryset.managed_by(self.request.user)
        unit_field.required = True
        if self.object and self.object.pk:
            unit_field.disabled = True
        return form

    def forms_valid(self, form, period_formset_with_days, resource_image_formset):
        self.object = form.save()

        self._delete_extra_periods_days(period_formset_with_days)
        period_formset_with_days.instance = self.object
        period_formset_with_days.save()

        self._save_resource_purposes()
        self._delete_extra_images(resource_image_formset)
        self._save_resource_images(resource_image_formset)
        self.object.update_opening_hours()

        return HttpResponseRedirect(self.get_success_url())

    def forms_invalid(self, form, period_formset_with_days, resource_image_formset):
        messages.error(self.request, 'Tallennus epäonnistui. Tarkista lomakkeen virheet.')

        # Extra forms are not added upon post so they
        # need to be added manually below. This is because
        # the front-end uses the empty 'extra' forms for cloning.
        temp_image_formset = get_resource_image_formset()
        temp_period_formset = get_period_formset()
        temp_day_form = temp_period_formset.forms[0].days.forms[0]

        resource_image_formset.forms.append(temp_image_formset.forms[0])
        period_formset_with_days.forms.append(temp_period_formset.forms[0])

        # Add a nested empty day to each period as well.
        for period in period_formset_with_days:
            period.days.forms.append(temp_day_form)

        trans_fields = forms.get_translated_field_count(resource_image_formset)

        return self.render_to_response(
            self.get_context_data(
                form=form,
                period_formset_with_days=period_formset_with_days,
                resource_image_formset=resource_image_formset,
                trans_fields=trans_fields,
                page_headline=_('Edit resource'),
            )
        )

    def _validate_forms(self, form, period_formset, image_formset):
        valid_form = form.is_valid()
        valid_period_form = period_formset.is_valid()
        valid_image_formset = image_formset.is_valid()

        return valid_form and valid_period_form and valid_image_formset

    def _save_resource_purposes(self):
        checked_purposes = self.request.POST.getlist('purposes')

        for purpose in checked_purposes:
            self.object.purposes.add(purpose)

    def _save_resource_images(self, resource_image_formset):
        count = len(resource_image_formset)

        for i in range(count):
            resource_image = resource_image_formset.forms[i].save(commit=False)
            resource_image.resource = self.object
            image_key = 'images-' + str(i) + '-image'

            if image_key in self.request.FILES:
                resource_image.image = self.request.FILES[image_key]

            resource_image.save()

    def _delete_extra_images(self, resource_images_formset):
        data = resource_images_formset.data
        image_ids = get_formset_ids('images', data)

        if image_ids is None:
            return

        ResourceImage.objects.filter(resource=self.object).exclude(pk__in=image_ids).delete()

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
