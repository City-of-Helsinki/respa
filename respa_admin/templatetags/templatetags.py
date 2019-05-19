from django import template


register = template.Library()


@register.filter
def instances_and_widgets(bound_field):
    """
    Returns a list of two-tuples of instances and widgets, designed to
    be used with ModelMultipleChoiceField and CheckboxSelectMultiple widgets.

    Allows templates to loop over a multiple checkbox field and display the
    related model instance, such as for a table with checkboxes.

    Usage:
       {% for instance, widget in form.my_field_name|instances_and_widgets %}
           <p>{{ instance }}: {{ widget }}</p>
       {% endfor %}

    Source: https://stackoverflow.com/a/27545910
    """
    instance_widgets = []
    for index, instance in enumerate(bound_field.field.queryset.all()):
        widget = copy(bound_field[index])
        # Hide the choice label so it just renders as a checkbox
        widget.choice_label = ''
        instance_widgets.append((instance, widget))
    return instance_widgets


@register.filter
def get_value_from_dict(dict_data, key):
    """
    Usage example {{ your_dict|get_value_from_dict:your_key }}.
    """
    if key:
        return dict_data.get(key)
