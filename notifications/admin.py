from parler.admin import TranslatableAdmin
from django.contrib import admin
from django.contrib.admin import site as admin_site

from .models import NotificationTemplate


class NotificationTemplateAdmin(TranslatableAdmin):
    #
    # When attempting to save, validate Jinja templates based on
    # example data. Possible to get an exception if unknown context
    # variables are accessed?
    #
    pass


admin_site.register(NotificationTemplate, NotificationTemplateAdmin)
