from django import forms


class RespaRadioSelect(forms.RadioSelect):
    template_name = 'forms/_radio.html'
    option_template_name = 'forms/_radio_option.html'


class RespaCheckboxSelect(forms.CheckboxSelectMultiple):
    template_name = 'forms/_checkbox_select.html'
    option_template_name = 'forms/_checkbox_select_option.html'
