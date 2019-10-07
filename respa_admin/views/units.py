from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import FieldDoesNotExist
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils.translation import ugettext as _
from django.views.generic import CreateView, ListView
from resources.enums import UnitAuthorizationLevel
from resources.models import Unit, UnitAuthorization
from respa_admin.forms import (
    get_translated_field_count,
    UnitForm,
)
from respa_admin.views.base import ExtraContextMixin, PeriodMixin


class UnitListView(ExtraContextMixin, ListView):
    model = Unit
    paginate_by = 10
    context_object_name = 'units'
    template_name = 'respa_admin/page_units.html'

    def get(self, request, *args, **kwargs):
        get_params = request.GET
        self.search_query = get_params.get('search_query')
        self.order_by = get_params.get('order_by', 'name')
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['search_query'] = self.search_query or ''
        context['order_by'] = self.order_by
        return context

    def get_managed_units_queryset(self):
        qs = super().get_queryset()
        qs = qs.managed_by(self.request.user)
        return qs

    def get_queryset(self):
        qs = self.get_managed_units_queryset()

        if self.search_query:
            qs = qs.filter(name__icontains=self.search_query)
        if self.order_by:
            order_by_param = self.order_by.strip('-')
            try:
                if Unit._meta.get_field(order_by_param):
                    qs = qs.order_by(self.order_by)
            except FieldDoesNotExist:
                pass
        return qs


class UnitEditView(ExtraContextMixin, PeriodMixin, CreateView):
    """
    View for saving new units and updating existing units.
    """
    http_method_names = ['get', 'post']
    model = Unit
    pk_url_kwarg = 'unit_id'
    form_class = UnitForm
    template_name = 'respa_admin/units/create_unit.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if settings.RESPA_ADMIN_VIEW_UNIT_URL and self.object:
            context['RESPA_ADMIN_VIEW_UNIT_URL'] = settings.RESPA_ADMIN_VIEW_UNIT_URL + self.object.id
        else:
            context['RESPA_ADMIN_VIEW_UNIT_URL'] = ''
        return context

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.managed_by(self.request.user)

    def get_success_url(self, **kwargs):
        messages.success(self.request, _('Unit saved'))
        return reverse_lazy('respa_admin:edit-unit', kwargs={
            self.pk_url_kwarg: self.object.id,
        })

    def get(self, request, *args, **kwargs):
        if self.pk_url_kwarg in kwargs:
            self.object = self.get_object()
            page_headline = _('Edit unit')
        else:
            page_headline = _('Create new unit')
            self.object = None

        form = self.get_form()

        trans_fields = get_translated_field_count()

        return self.render_to_response(
            self.get_context_data(
                form=form,
                trans_fields=trans_fields,
                page_headline=page_headline,
            )
        )

    def post(self, request, *args, **kwargs):
        if self.pk_url_kwarg in kwargs:
            self.object = self.get_object()
            if not (self.object.is_admin(request.user) or self.object.is_manager(request.user)):
                # only unit admins or managers can edit units
                raise PermissionDenied
            if not self.object.is_editable():
                # unit with imported data can not be edited
                raise PermissionDenied
        else:
            self.object = None

        if self.object is None:
            # Creating new units is currently disabled
            return HttpResponse(status_code=404)

        form = self.get_form()
        period_formset_with_days = self.get_period_formset()

        if self._validate_forms(form, period_formset_with_days):
            return self.forms_valid(form, period_formset_with_days)
        else:
            return self.forms_invalid(form, period_formset_with_days)

    def forms_valid(self, form, period_formset_with_days):
        is_creating_new = self.object is None
        self.object = form.save()
        self.save_period_formset(period_formset_with_days)

        if is_creating_new:
            UnitAuthorization.objects.create(
                subject=self.object, authorized=self.request.user, level=UnitAuthorizationLevel.admin)

        return HttpResponseRedirect(self.get_success_url())

    def forms_invalid(self, form, period_formset_with_days):
        messages.error(self.request, _('Saving failed. Check error in the form.'))
        period_formset_with_days = self.add_empty_forms(period_formset_with_days)
        trans_fields = get_translated_field_count()
        return self.render_to_response(
            self.get_context_data(
                form=form,
                period_formset_with_days=period_formset_with_days,
                trans_fields=trans_fields,
                page_headline=_('Edit Unit'),
            )
        )

    def _validate_forms(self, form, period_formset):
        valid_form = form.is_valid()
        valid_period_form = period_formset.is_valid()
        return valid_form and valid_period_form
