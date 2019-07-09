from django.apps import AppConfig
from django.conf import settings


class PaymentsConfig(AppConfig):
    name = 'payments'

    def ready(self):
        """Verify active payment provider configuration"""
        if settings.RESPA_PAYMENTS_ENABLED:
            from .providers import load_provider_config
            load_provider_config()
