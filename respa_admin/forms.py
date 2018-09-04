from django import forms
from django.forms import inlineformset_factory

from .widgets import (
    RespaRadioSelect,
    RespaCheckboxSelect
)

from resources.models import (
    Day,
    Equipment,
    Period,
    Purpose,
    Resource,
    ResourceImage,
)


class DaysForm(forms.ModelForm):
    opens = forms.TimeField(
        widget=forms.TimeInput(
            format='%H:%M',
            attrs={'class': 'text-input form-control', 'type': 'time'}
        )
    )

    closes = forms.TimeField(
        widget=forms.TimeInput(
            format='%H:%M',
            attrs={'class': 'text-input form-control', 'type': 'time'}
        )
    )

    class Meta:
        model = Day
        fields = ['weekday', 'opens', 'closes', 'closed']


class PeriodForm(forms.ModelForm):
    name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': 'text-input form-control'})
    )
    start = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={'class': 'text-input form-control', 'type': 'date'})
    )
    end = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={'class': 'text-input form-control', 'type': 'date'})
    )

    class Meta:
        model = Period
        fields = ['name', 'start', 'end']


class ImageForm(forms.ModelForm):

    class Meta:
        model = ResourceImage
        fields = ['image', 'caption', 'type']


class ResourceForm(forms.ModelForm):
    purposes = forms.ModelMultipleChoiceField(
        widget=RespaCheckboxSelect,
        queryset=Purpose.objects.all(),
        required=True,
    )

    equipment = forms.ModelMultipleChoiceField(
        required=False,
        widget=RespaCheckboxSelect,
        queryset=Equipment.objects.all(),
    )

    class Meta:
        model = Resource
        fields = [
            'unit',
            'type',
            'name',
            'description',
            'purposes',
            'equipment',
            'responsible_contact_info',  # These fields ought to be atomic.
            'people_capacity',
            'area',
            'min_period',
            'max_period',
            'reservable_days_in_advance',
            'max_reservations_per_user',
            'reservable',
            'reservation_info',
            'need_manual_confirmation',
            'authentication',
            'access_code_type',
            'max_price_per_hour',
            'min_price_per_hour',
            'generic_terms',
            'specific_terms',
            'reservation_confirmed_notification_extra',
            'public',
        ]
        widgets = {
            'min_period': forms.Select(
                choices=(
                    ('00:30:00', '30 min'),
                    ('00:45:00', '45 min'),
                    ('01:00:00', '60 min'),
                )
            ),
            'max_period': forms.Select(
                choices=(
                    ('00:30:00', '30 min'),
                    ('00:45:00', '45 min'),
                    ('01:00:00', '60 min'),
                )
            ),
            'need_manual_confirmation': RespaRadioSelect(
                choices=((True, 'Kyllä'), (False, 'Ei'))
            ),
            'public': forms.Select(
                choices=((False, 'Piilotettu'), (True, 'Julkaistu'))
            ),
            'reservable': forms.Select(
                choices=((False, 'Ei varattavissa'), (True, 'Varattavissa'))
            ),
        }


class PeriodFormset(forms.BaseInlineFormSet):

    def _get_days_formset(self, form, extra_days=1):
        days_formset = inlineformset_factory(
            Period,
            Day,
            form=DaysForm,
            extra=extra_days,
            validate_max=True
        )

        return days_formset(
            instance=form.instance,
            data=form.data if form.is_bound else None,
            prefix='days-%s' % (
                form.prefix,
            ),
        )

    def add_fields(self, form, index):
        super(PeriodFormset, self).add_fields(form, index)
        form.days = self._get_days_formset(form=form)

    def is_valid(self):
        valid_form = super(PeriodFormset, self).is_valid()
        if not valid_form:
            return valid_form

        # Do additional checks on top of the built in checks to
        # validate that nested days are also valid
        valid_days = []
        for form in self.forms:
            valid_days.append(form.days.is_valid())
            if not form.days.is_valid():
                form.add_error(None, 'Tarkista aukioloajat.')

        return valid_form and all(valid_days)

    def save(self, commit=True):
        saved_form = super(PeriodFormset, self).save(commit=commit)

        if saved_form or self.forms:
            for form in self.forms:
                form.save(commit=commit)
                if hasattr(form, 'days'):
                    form.days.save(commit=commit)

        return saved_form


def get_period_formset(request=None, extra=1, instance=None):
    period_formset_with_days = inlineformset_factory(
        Resource,
        Period,
        fk_name='resource',
        form=PeriodForm,
        formset=PeriodFormset,
        extra=extra,
    )

    if not request:
        return period_formset_with_days(instance=instance)
    if request.method == 'GET':
        return period_formset_with_days(instance=instance)
    else:
        return period_formset_with_days(data=request.POST, instance=instance)


def get_resource_image_formset(request=None, extra=1, instance=None):
    resource_image_formset = inlineformset_factory(
        Resource,
        ResourceImage,
        form=ImageForm,
        extra=extra,
    )

    if not request:
        return resource_image_formset(instance=instance)
    if request.method == 'GET':
        return resource_image_formset(instance=instance)
    else:
        return resource_image_formset(data=request.POST, files=request.FILES, instance=instance)
