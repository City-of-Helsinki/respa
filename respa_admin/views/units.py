from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import FieldDoesNotExist
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils.translation import ugettext as _
from django.views.generic import CreateView, ListView
from resources.enums import UnitAuthorizationLevel
from resources.models import Day, Period, Unit, UnitAuthorization
from respa_admin.forms import (
    get_period_formset,
    get_translated_field_count,
    UnitForm,
)
from respa_admin.views.base import ExtraContextMixin


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


class UnitEditView(ExtraContextMixin, CreateView):
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

        period_formset_with_days = get_period_formset(
            self.request,
            instance=self.object,
            parent_class=Unit
        )

        trans_fields = get_translated_field_count()

        return self.render_to_response(
            self.get_context_data(
                form=form,
                period_formset_with_days=period_formset_with_days,
                trans_fields=trans_fields,
                page_headline=page_headline,
            )
        )

    def post(self, request, *args, **kwargs):
        if self.pk_url_kwarg in kwargs:
            self.object = self.get_object()
            if not (self.object.is_admin(request.user) or self.object.is_manager(request.user)):
                raise PermissionDenied
        else:
            self.object = None

        if self.object is None:
            # Creating new units is currently disabled
            return HttpResponse(status_code=404)

        form = self.get_form()

        period_formset_with_days = get_period_formset(request=request, instance=self.object, parent_class=Unit)

        if self._validate_forms(form, period_formset_with_days):
            return self.forms_valid(form, period_formset_with_days)
        else:
            return self.forms_invalid(form, period_formset_with_days)

    def forms_valid(self, form, period_formset_with_days):
        is_creating_new = self.object is None
        self.object = form.save()

        self._delete_extra_periods_days(period_formset_with_days)
        period_formset_with_days.instance = self.object
        period_formset_with_days.save()
        self.object.update_opening_hours()
        if is_creating_new:
            UnitAuthorization.objects.create(
                subject=self.object, authorized=self.request.user, level=UnitAuthorizationLevel.admin)

        return HttpResponseRedirect(self.get_success_url())

    def forms_invalid(self, form, period_formset_with_days):
        messages.error(self.request, _('Saving failed. Check error in the form.'))

        # Extra forms are not added upon post so they
        # need to be added manually below. This is because
        # the front-end uses the empty 'extra' forms for cloning.
        temp_period_formset = get_period_formset()
        temp_day_form = temp_period_formset.forms[0].days.forms[0]

        period_formset_with_days.forms.append(temp_period_formset.forms[0])

        # Add a nested empty day to each period as well.
        for period in period_formset_with_days:
            period.days.forms.append(temp_day_form)

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

    def _delete_extra_periods_days(self, period_formset_with_days):
        data = period_formset_with_days.data
        period_ids = get_formset_ids('periods', data)

        if period_ids is None:
            return

        Period.objects.filter(unit=self.object).exclude(pk__in=period_ids).delete()
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
