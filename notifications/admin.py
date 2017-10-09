from parler.admin import TranslatableAdmin
from parler.forms import TranslatableModelForm
from django.contrib.admin import site as admin_site
from .models import NotificationTemplate


class NotificationTemplateForm(TranslatableModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Do not allow the admin to choose any of the template types that already
        # exist.
        qs = NotificationTemplate.objects.values_list('type', flat=True)
        if self.instance and self.instance.type:
            qs = qs.exclude(id=self.instance.id)
        existing_types = set(qs)
        choices = [x for x in self.fields['type'].choices if x[0] not in existing_types]
        self.fields['type'].choices = choices


class NotificationTemplateAdmin(TranslatableAdmin):
    #
    # When attempting to save, validate Jinja templates based on
    # example data. Possible to get an exception if unknown context
    # variables are accessed?
    #
    form = NotificationTemplateForm


admin_site.register(NotificationTemplate, NotificationTemplateAdmin)
