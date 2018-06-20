from django import forms


class RespaRadioSelect(forms.RadioSelect):
    template_name = 'forms/_radio.html'
    option_template_name = 'forms/_radio_option.html'
