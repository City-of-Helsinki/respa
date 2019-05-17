from django.conf import settings


class ExtraContextMixin():
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['INSTRUCTIONS_URL'] = settings.RESPA_ADMIN_INSTRUCTIONS_URL
        context['SUPPORT_EMAIL'] = settings.RESPA_ADMIN_SUPPORT_EMAIL
        return context
