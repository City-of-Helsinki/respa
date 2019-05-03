import environ

from django.conf import settings
from django.utils.module_loading import import_string

_payment_provider = None


def get_payment_provider():
    """Load and cache the active payment provider"""
    global _payment_provider
    if not _payment_provider:

        # Provider path is the only thing loaded from env
        # in the global settings, the rest are added here
        provider_path = getattr(settings, 'RESPA_PAYMENTS_PROVIDER')
        provider = import_string(provider_path)

        # Provider tells what keys and types it requires for configuration
        # and the corresponding data has to be set in .env
        template = provider.get_config_template()
        env = environ.Env(**template)

        config = {}
        for key in template.keys():
            if hasattr(settings, key):
                config[key] = getattr(settings, key)
            else:
                config[key] = env(key)

        _payment_provider = provider(PAYMENT_CONFIG=config)

    return _payment_provider
