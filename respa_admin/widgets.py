from django import forms


class RespaRadioSelect(forms.RadioSelect):
    template_name = 'respa_admin/forms/widgets/_radio.html'
    option_template_name = 'respa_admin/forms/widgets/_radio_option.html'


class RespaCheckboxSelect(forms.CheckboxSelectMultiple):
    template_name = 'respa_admin/forms/widgets/_checkbox_select.html'
    option_template_name = 'respa_admin/forms/widgets/_checkbox_select_option.html'


class RespaCheckboxInput(forms.CheckboxInput):
    template_name = 'respa_admin/forms/widgets/_checkbox.html'


class RespaImageSelectWidget(forms.ClearableFileInput):
    template_name = 'respa_admin/forms/_image.html'


class RespaImageSelectField(forms.ImageField):
    widget = RespaImageSelectWidget()
