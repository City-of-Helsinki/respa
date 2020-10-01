from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from resources.auth import is_any_admin
from resources.models import Day, Period
from respa_admin.forms import get_period_formset


class ExtraContextMixin():
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['INSTRUCTIONS_URL'] = settings.RESPA_ADMIN_INSTRUCTIONS_URL
        context['SUPPORT_EMAIL'] = settings.RESPA_ADMIN_SUPPORT_EMAIL
        if settings.RESPA_ADMIN_LOGO:
            context['logo_url'] = staticfiles_storage.url('respa_admin/img/{0}'.format(settings.RESPA_ADMIN_LOGO))
        context['KORO_STYLE'] = settings.RESPA_ADMIN_KORO_STYLE
        context['user_is_any_admin'] = is_any_admin(self.request.user)
        return context


class PeriodMixin():
    """ Common functionality for views handling opening hour periods.
        Must be used in a CreateView or UpdateView where, expects class attributes
        such as self.object and self.model.
    """
    def get_context_data(self, **kwargs):
        is_formset_in_kwargs = 'period_formset_with_days' in kwargs
        context = super().get_context_data(**kwargs)
        # If formset is passed explicitly via kwargs, do not override
        if not is_formset_in_kwargs:
            context['period_formset_with_days'] = self.get_period_formset()
        return context

    def get_period_formset(self):
        return get_period_formset(
            self.request,
            instance=self.object,
            parent_class=self.model,
        )

    def save_period_formset(self, period_formset):
        self._delete_extra_periods_days(period_formset)
        period_formset.instance = self.object
        period_formset.save()
        self.object.update_opening_hours()

    def add_empty_forms(self, period_formset):
        # Extra forms are not added upon post so they
        # need to be added manually below. This is because
        # the front-end uses the empty 'extra' forms for cloning.
        temp_period_formset = get_period_formset()
        temp_day_form = temp_period_formset.forms[0].days.forms[0]
        period_formset.forms.append(temp_period_formset.forms[0])
        # Add a nested empty day to each period as well.
        for period in period_formset:
            period.days.forms.append(temp_day_form)
        return period_formset

    def _delete_extra_periods_days(self, period_formset_with_days):
        data = period_formset_with_days.data
        period_ids = self.get_formset_ids('periods', data)

        if period_ids is None:
            return

        period_filter_args = {self.object._meta.model_name: self.object}
        Period.objects.filter(**period_filter_args).exclude(pk__in=period_ids).delete()
        period_count = self.to_int(data.get('periods-TOTAL_FORMS'))

        if not period_count:
            return

        for i in range(period_count):
            period_id = self.to_int(data.get('periods-{}-id'.format(i)))

            if period_id is None:
                continue

            day_ids = self.get_formset_ids('days-periods-{}'.format(i), data)
            if day_ids is not None:
                Day.objects.filter(period=period_id).exclude(pk__in=day_ids).delete()

    def get_formset_ids(self, formset_name, data):
        count = self.to_int(data.get('{}-TOTAL_FORMS'.format(formset_name)))
        if count is None:
            return None

        ids_or_nones = (
            self.to_int(data.get('{}-{}-{}'.format(formset_name, i, 'id')))
            for i in range(count)
        )

        return {x for x in ids_or_nones if x is not None}

    def to_int(self, string):
        if not string or not string.isdigit():
            return None
        return int(string)
