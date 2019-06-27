import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test.utils import override_settings

from ..providers import get_payment_provider

PAYMENTS_ENABLED = True
PROVIDER_CLASS = 'payments.providers.BamboraPayformProvider'
API_URL = 'https://my-awesome-provider/api'
API_KEY = 'dummy-key'
API_SECRET = 'dummy-secret'
PAYMENT_METHODS = ['dummy-bank', 'dummy-cards']


def test_payment_provider_load_configuration_missing_target():
    """Test provider init fails when no configuration is given"""
    with pytest.raises(ImportError):
        get_payment_provider()


@override_settings(RESPA_PAYMENTS_ENABLED=PAYMENTS_ENABLED)
@override_settings(RESPA_PAYMENTS_PROVIDER_CLASS=PROVIDER_CLASS)
def test_payment_provider_load_configuration_missing_settings():
    """Test provider init raises improperly configured when missing required settings"""
    with pytest.raises(ImproperlyConfigured):
        get_payment_provider()


@override_settings(RESPA_PAYMENTS_ENABLED=PAYMENTS_ENABLED)
@override_settings(RESPA_PAYMENTS_PROVIDER_CLASS=PROVIDER_CLASS)
@override_settings(RESPA_PAYMENTS_BAMBORA_API_URL=API_URL)
@override_settings(RESPA_PAYMENTS_BAMBORA_API_KEY=API_KEY)
@override_settings(RESPA_PAYMENTS_BAMBORA_API_SECRET=API_SECRET)
@override_settings(RESPA_PAYMENTS_BAMBORA_PAYMENT_METHODS=PAYMENT_METHODS)
def test_payment_provider_load_configuration_settings_success():
    """Test provider init works when all required values are present in settings"""
    provider = get_payment_provider()
    assert provider.url_payment_api == API_URL
