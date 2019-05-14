import environ

from django.conf import settings
from django.utils.module_loading import import_string

_active_provider = None


def get_payment_provider():
    """Load and cache the active payment provider"""
    global _active_provider
    if not _active_provider:

        # Provider path is the only thing loaded from env
        # in the global settings, the rest are added here
        provider_path = getattr(settings, 'RESPA_PAYMENTS_PROVIDER_CLASS')
        provider_class = import_string(provider_path)

        # Provider tells what keys and types it requires for configuration
        # and the corresponding data has to be set in .env
        template = provider_class.get_config_template()
        env = environ.Env(**template)

        config = {}
        for key in template.keys():
            if hasattr(settings, key):
                config[key] = getattr(settings, key)
            else:
                config[key] = env(key)

        _active_provider = provider_class(PAYMENT_CONFIG=config)

    return _active_provider
