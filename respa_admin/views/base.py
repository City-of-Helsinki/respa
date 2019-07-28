from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage


class ExtraContextMixin():
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['INSTRUCTIONS_URL'] = settings.RESPA_ADMIN_INSTRUCTIONS_URL
        context['SUPPORT_EMAIL'] = settings.RESPA_ADMIN_SUPPORT_EMAIL
        if settings.RESPA_ADMIN_LOGO:
            context['logo_url'] = staticfiles_storage.url('respa_admin/img/{0}'.format(settings.RESPA_ADMIN_LOGO))
        context['KORO_STYLE'] = settings.RESPA_ADMIN_KORO_STYLE
        return context
