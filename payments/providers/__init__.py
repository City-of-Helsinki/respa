import environ
from django.conf import settings
from django.http import HttpRequest
from django.utils.module_loading import import_string

from .bambora_payform import BamboraPayformProvider  # noqa
# imported here so that we can refer to it like 'payments.providers.BamboraPayformProvider'
from .base import PaymentProvider

_provider_class = None


def load_provider_config():
    """Initialize the active payment provider config dict

    Also verifies that all config params the provider requires are present"""
    global _provider_class

    # Provider path is the only thing loaded from env
    # in the global settings, the rest are added here
    provider_path = getattr(settings, 'RESPA_PAYMENTS_PROVIDER_CLASS')
    _provider_class = import_string(provider_path)

    # Provider tells what keys and types it requires for configuration
    # and the corresponding data has to be set in .env
    template = _provider_class.get_config_template()
    env = environ.Env(**template)

    config = {}
    for key in template.keys():
        if hasattr(settings, key):
            config[key] = getattr(settings, key)
        else:
            config[key] = env(key)

    _provider_class.config = config


def get_payment_provider(request: HttpRequest, ui_return_url: str = None) -> PaymentProvider:
    """Get a new instance of the active payment provider with associated request
    and optional return_url info"""
    return _provider_class(request=request, ui_return_url=ui_return_url)
