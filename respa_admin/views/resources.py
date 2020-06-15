from django.conf import settings
from django.contrib import messages
from django.db.models import FieldDoesNotExist, Q
from django.http import Http404, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django.views.generic import CreateView, ListView, UpdateView
from guardian.shortcuts import assign_perm, remove_perm
from respa_admin.views.base import ExtraContextMixin
from resources.enums import UnitGroupAuthorizationLevel, UnitAuthorizationLevel
from resources.auth import is_any_admin

from users.models import User

from resources.models import (
    Resource,
    Period,
    Day,
    ResourceImage,
    ResourceType,
    Unit,
    UnitGroup
)
from respa_admin import accessibility_api, forms
from respa_admin.forms import (
    ResourceForm,
    UserForm,
    get_period_formset,
    get_resource_image_formset,
    get_unit_authorization_formset
)
from respa_admin.views.base import PeriodMixin


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
        context['search_query'] = self.search_query or ''
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


class ManageUserPermissionsView(ExtraContextMixin, UpdateView):
    model = User
    context_object_name = 'user_object'
    pk_url_kwarg = 'user_id'
    form_class = UserForm
    template_name = 'respa_admin/resources/edit_user.html'

    def get_success_url(self, **kwargs):
        return reverse_lazy('respa_admin:edit-user', kwargs={'user_id': self.object.pk})

    def _validate_forms(self, form, unit_authorization_formset):
        valid_form = form.is_valid()
        valid_unit_authorization_formset = unit_authorization_formset.is_valid()

        if valid_unit_authorization_formset:
            perms_are_empty_or_marked_for_deletion = all(
                {"DELETE": True}.items() <= dict.items() or len(dict) == 0
                for dict in unit_authorization_formset.cleaned_data
            )

        if not form.cleaned_data['is_staff'] and not perms_are_empty_or_marked_for_deletion:
            form.add_error(None, _('You can\'t remove staff status from user with existing permissions'))
            return False

        return valid_form and valid_unit_authorization_formset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unit_authorization_formset'] = get_unit_authorization_formset(
            request=self.request,
            instance=self.object,
        )
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()

        unit_authorization_formset = get_unit_authorization_formset(request=request, instance=self.get_object())

        if self._validate_forms(form, unit_authorization_formset):
            return self.forms_valid(form, unit_authorization_formset)
        else:
            return self.forms_invalid(form, unit_authorization_formset)

    def forms_valid(self, form, unit_authorization_formset):
        self.object = form.save()
        unit_authorization_formset.instance = self.object
        for form in unit_authorization_formset.cleaned_data:
            if 'subject' in form and 'level' in form:
                if form['can_approve_reservation']:
                    assign_perm('unit:can_approve_reservation', self.object, form['subject'])
                else:
                    remove_perm('unit:can_approve_reservation', self.object, form['subject'])

        unit_authorization_formset.save()
        return HttpResponseRedirect(self.get_success_url())

    def forms_invalid(self, form, unit_authorization_formset):
        messages.error(self.request, _('Failed to save. Please check the form for errors.'))

        return self.render_to_response(
            self.get_context_data(
                form=form,
                unit_authorization_formset=unit_authorization_formset,
            )
        )


class ManageUserPermissionsListView(ExtraContextMixin, ListView):
    model = Unit
    context_object_name = 'units'
    template_name = 'respa_admin/user_management.html'
    user_list_template_name = 'respa_admin/resources/_unit_user_list.html'
    paginate_by = 10

    def get(self, request, *args, **kwargs):
        get_params = request.GET
        self.selected_unit = get_params.get('selected_unit')
        return super().get(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        if not is_any_admin(request.user):
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get_all_available_units(self):
        if self.request.user.is_superuser:
            all_units = self.model.objects.all().prefetch_related('authorizations').exclude(authorizations__authorized__isnull=True)
            return all_units

        unit_filters = Q(authorizations__authorized=self.request.user,
                         authorizations__level__in={
                             UnitAuthorizationLevel.admin,
                         })
        unit_group_filters = Q(unit_groups__authorizations__authorized=self.request.user,
                               unit_groups__authorizations__level__in={
                                   UnitGroupAuthorizationLevel.admin,
                               })
        all_available_units = self.model.objects.filter(unit_filters | unit_group_filters).prefetch_related('authorizations')
        return all_available_units.exclude(authorizations__authorized__isnull=True).distinct('name')

    def get_queryset(self):
        qs = self.get_all_available_units()
        if self.selected_unit:
            qs = qs.filter(id=self.selected_unit)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['selected_unit'] = self.selected_unit or ''
        context['all_available_units'] = self.get_all_available_units()
        context['user_list_template_name'] = self.user_list_template_name
        return context


class ManageUserPermissionsSearchView(ExtraContextMixin, ListView):
    model = User
    context_object_name = 'users'
    template_name = 'respa_admin/user_management.html'
    user_list_template_name = 'respa_admin/resources/_user_list.html'

    def get(self, request, *args, **kwargs):
        get_params = request.GET
        self.search_query = get_params.get('search_query')
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        if self.search_query and '@' in self.search_query:
            qs = self.model.objects.filter(email__iexact=self.search_query)
            return qs
        elif self.search_query and ' ' in self.search_query:
            try:
                name1, name2 = self.search_query.split()
                filters = Q(first_name__iexact=name1, last_name__iexact=name2) | Q(first_name__iexact=name2, last_name__iexact=name1)
                qs = self.model.objects.filter(filters)
                return qs
            except ValueError:
                return qs
        return self.model.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['user_list_template_name'] = self.user_list_template_name
        context['search_query'] = self.search_query or None

        return context


class RespaAdminIndex(ResourceListView):
    paginate_by = 7
    template_name = 'respa_admin/index.html'


def admin_office(request):
    return TemplateResponse(request, 'respa_admin/page_office.html')


class SaveResourceView(ExtraContextMixin, PeriodMixin, CreateView):
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
        if settings.RESPA_ADMIN_VIEW_RESOURCE_URL and self.object:
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
        location_id = str(self.object.unit.id).lstrip('tprek:')  # remove prefix, use bare tprek id
        user = request.user.email or request.user.username
        return accessibility_api.generate_url(
            api_url,
            system_id,
            target_id,
            target_name,
            user,
            secret,
            location_id=location_id
        )

    def post(self, request, *args, **kwargs):
        if self.pk_url_kwarg in kwargs:
            self.object = self.get_object()
        else:
            self.object = None

        form = self.get_form()

        period_formset_with_days = self.get_period_formset()
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
        self._save_resource_purposes()
        self._delete_extra_images(resource_image_formset)
        self._save_resource_images(resource_image_formset)
        self.save_period_formset(period_formset_with_days)
        return HttpResponseRedirect(self.get_success_url())

    def forms_invalid(self, form, period_formset_with_days, resource_image_formset):
        messages.error(self.request, _('Failed to save. Please check the form for errors.'))

        # Extra forms are not added upon post so they
        # need to be added manually below. This is because
        # the front-end uses the empty 'extra' forms for cloning.
        temp_image_formset = get_resource_image_formset()
        resource_image_formset.forms.append(temp_image_formset.forms[0])
        period_formset_with_days = self.add_empty_forms(period_formset_with_days)
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
