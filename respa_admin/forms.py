from django.utils.translation import ugettext_lazy as _
from django import forms
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory

from .widgets import (
    RespaRadioSelect,
    RespaCheckboxSelect,
    RespaCheckboxInput,
)

from resources.models import (
    Day,
    Equipment,
    Period,
    Purpose,
    Resource,
    ResourceImage,
)

from respa.settings import LANGUAGES


class DaysForm(forms.ModelForm):
    opens = forms.TimeField(
        required=False,
        widget=forms.TimeInput(
            format='%H:%M',
            attrs={'class': 'text-input form-control',
                   'placeholder': 'hh:mm'}
        )
    )

    closes = forms.TimeField(
        required=False,
        widget=forms.TimeInput(
            format='%H:%M',
            attrs={'class': 'text-input form-control',
                   'placeholder': 'hh:mm'}
        )
    )

    closed = forms.NullBooleanField(
        widget=RespaCheckboxInput,
    )

    class Meta:
        model = Day
        fields = ['weekday', 'opens', 'closes', 'closed']

    def clean(self):
        cleaned_data = super().clean()
        is_empty_hours = not cleaned_data['opens'] or not cleaned_data['closes']
        is_closed = cleaned_data['closed']
        if is_empty_hours and not is_closed:
            raise ValidationError('Missing opening hours')
        return cleaned_data


class PeriodForm(forms.ModelForm):
    name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': 'text-input form-control'})
    )

    start = forms.DateField(
        required=True,
        widget=forms.DateInput(
            attrs={
                'class': 'text-input form-control datepicker',
                'data-provide': 'datepicker',
                'data-date-format': _("yyyy-mm-dd"),
                'data-date-language': 'fi',
            }
        )
    )

    end = forms.DateField(
        required=True,
        widget=forms.DateInput(
            attrs={
                'class': 'text-input form-control datepicker',
                'data-provide': 'datepicker',
                'data-date-format': _("yyyy-mm-dd"),
                'data-date-language': 'fi',
            }
        )
    )

    class Meta:
        model = Period
        fields = ['name', 'start', 'end']


class ImageForm(forms.ModelForm):
    class Meta:
        model = ResourceImage
        translated_fields = ['caption_fi', 'caption_en', 'caption_sv']
        fields = ['image', 'type'] + translated_fields


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

    name_fi = forms.CharField(
        required=True,
        label='Nimi [fi]',
    )

    class Meta:
        model = Resource

        translated_fields = [
            'name_fi',
            'name_en',
            'name_sv',
            'description_fi',
            'description_en',
            'description_sv',
            'reservation_info_fi',
            'reservation_info_en',
            'reservation_info_sv',
            'specific_terms_fi',
            'specific_terms_en',
            'specific_terms_sv',
            'reservation_requested_notification_extra_fi',
            'reservation_requested_notification_extra_en',
            'reservation_requested_notification_extra_sv',
            'reservation_confirmed_notification_extra_fi',
            'reservation_confirmed_notification_extra_en',
            'reservation_confirmed_notification_extra_sv',
            'responsible_contact_info_fi',
            'responsible_contact_info_en',
            'responsible_contact_info_sv',
        ]

        fields = [
            'unit',
            'type',
            'purposes',
            'equipment',
            'external_reservation_url',
            'people_capacity',
            'area',
            'min_period',
            'max_period',
            'reservable_max_days_in_advance',
            'reservable_min_days_in_advance',
            'max_reservations_per_user',
            'reservable',
            'need_manual_confirmation',
            'authentication',
            'access_code_type',
            'max_price_per_hour',
            'min_price_per_hour',
            'generic_terms',
            'public',
            'reservation_metadata_set',
        ] + translated_fields

        widgets = {
            'min_period': forms.Select(
                choices=(
                    ('00:30:00', '0,5 h'),
                    ('01:00:00', '1 h'),
                    ('01:30:00', '1,5 h'),
                    ('02:00:00', '2 h'),
                    ('02:30:00', '2,5 h'),
                    ('03:00:00', '3 h'),
                    ('03:30:00', '3,5 h'),
                    ('04:00:00', '4 h'),
                    ('04:30:00', '4,5 h'),
                    ('05:00:00', '5 h'),
                    ('05:30:00', '5,5 h'),
                    ('06:00:00', '6 h'),
                    ('06:30:00', '6,5 h'),
                    ('07:00:00', '7 h'),
                    ('07:30:00', '7,5 h'),
                    ('08:00:00', '8 h'),
                    ('08:30:00', '8,5 h'),
                    ('09:00:00', '9 h'),
                    ('09:30:00', '9,5 h'),
                    ('10:00:00', '10 h'),
                    ('10:30:00', '10,5 h'),
                    ('11:00:00', '11 h'),
                    ('11:30:00', '11,5 h'),
                    ('12:00:00', '12 h'),
                    ('12:30:00', '12,5 h'),
                    ('13:00:00', '13 h'),
                    ('13:30:00', '13,5 h'),
                    ('14:00:00', '14 h'),
                    ('14:30:00', '14,5 h'),
                    ('15:00:00', '15 h'),
                    ('15:30:00', '15,5 h'),
                    ('16:00:00', '16 h'),
                    ('16:30:00', '16,5 h'),
                    ('17:00:00', '17 h'),
                    ('17:30:00', '17,5 h'),
                    ('18:00:00', '18 h'),
                    ('18:30:00', '18,5 h'),
                    ('19:00:00', '19 h'),
                    ('19:30:00', '19,5 h'),
                    ('20:00:00', '20 h'),
                    ('20:30:00', '20,5 h'),
                    ('21:00:00', '21 h'),
                    ('21:30:00', '21,5 h'),
                    ('22:00:00', '22 h'),
                    ('22:30:00', '22,5 h'),
                    ('23:00:00', '23 h'),
                    ('23:30:00', '23,5 h'),
                )
            ),
            'max_period': forms.Select(
                choices=(
                    ('00:30:00', '0,5 h'),
                    ('01:00:00', '1 h'),
                    ('01:30:00', '1,5 h'),
                    ('02:00:00', '2 h'),
                    ('02:30:00', '2,5 h'),
                    ('03:00:00', '3 h'),
                    ('03:30:00', '3,5 h'),
                    ('04:00:00', '4 h'),
                    ('04:30:00', '4,5 h'),
                    ('05:00:00', '5 h'),
                    ('05:30:00', '5,5 h'),
                    ('06:00:00', '6 h'),
                    ('06:30:00', '6,5 h'),
                    ('07:00:00', '7 h'),
                    ('07:30:00', '7,5 h'),
                    ('08:00:00', '8 h'),
                    ('08:30:00', '8,5 h'),
                    ('09:00:00', '9 h'),
                    ('09:30:00', '9,5 h'),
                    ('10:00:00', '10 h'),
                    ('10:30:00', '10,5 h'),
                    ('11:00:00', '11 h'),
                    ('11:30:00', '11,5 h'),
                    ('12:00:00', '12 h'),
                    ('12:30:00', '12,5 h'),
                    ('13:00:00', '13 h'),
                    ('13:30:00', '13,5 h'),
                    ('14:00:00', '14 h'),
                    ('14:30:00', '14,5 h'),
                    ('15:00:00', '15 h'),
                    ('15:30:00', '15,5 h'),
                    ('16:00:00', '16 h'),
                    ('16:30:00', '16,5 h'),
                    ('17:00:00', '17 h'),
                    ('17:30:00', '17,5 h'),
                    ('18:00:00', '18 h'),
                    ('18:30:00', '18,5 h'),
                    ('19:00:00', '19 h'),
                    ('19:30:00', '19,5 h'),
                    ('20:00:00', '20 h'),
                    ('20:30:00', '20,5 h'),
                    ('21:00:00', '21 h'),
                    ('21:30:00', '21,5 h'),
                    ('22:00:00', '22 h'),
                    ('22:30:00', '22,5 h'),
                    ('23:00:00', '23 h'),
                    ('23:30:00', '23,5 h'),
                )
            ),
            'need_manual_confirmation': RespaRadioSelect(
                choices=((True, _('Yes')), (False, _('No')))
            ),
            'public': forms.Select(
                choices=((False, _('Hidden')), (True, _('Published')))
            ),
            'reservable': forms.Select(
                choices=((False, _('Can not be reserved')), (True, _('Bookable')))
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
                form.add_error(None, _('Please check the opening hours.'))

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


def get_translated_field_count(image_formset):
    """
    Serve a count of how many fields are possible to translate with the translate
    buttons in the UI. The image formset is passed as a parameter since it can hold
    a number of forms with fields which can be translated.

    :param image_formset: formset holding images
    :return: dictionary of all languages as keys and the count of translated fields
    in corresponding language.
    """
    resource_form_data = ResourceForm.Meta.translated_fields
    translated_fields = resource_form_data
    lang_num = {}

    if translated_fields:
        for key, value in LANGUAGES:
            postfix = '_' + key
            images_fields_count = _get_images_formset_translated_fields(image_formset, postfix)
            lang_num[key] = sum(x.endswith(postfix) for x in translated_fields) + images_fields_count

    return lang_num


def _get_images_formset_translated_fields(images_formset, lang_postfix):
    image_forms = images_formset.forms
    images_translation_count = 0

    for form in image_forms:
        if form.initial:
            images_translation_count += len([x for x in form.initial if x.endswith(lang_postfix)])

    return images_translation_count
