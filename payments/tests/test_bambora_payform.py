import json

import pytest

from payments.providers.bambora_payform import (
    BamboraPayformProvider, DuplicateOrderError, PayloadValidationError, ServiceUnavailableError,
    UnknownReturnCodeError
)


@pytest.fixture()
def payment_provider():
    config = {
        'PAYMENT_BAMBORA_API_KEY': 'dummy-key',
        'PAYMENT_BAMBORA_API_SECRET': 'dummy-secret',
        'PAYMENT_BAMBORA_METHODS_ENABLED': ['dummy-bank']
    }
    return BamboraPayformProvider(PAYMENT_CONFIG=config)


def test_handle_order_create_success(payment_provider):
    """Test the response handler recognizes success and adds token as part of the returned url"""
    r = json.loads("""{
        "result": 0,
        "token": "abc123",
        "type": "e-payment"
    }""")
    return_value = payment_provider.handle_order_create(r)
    assert r['token'] in return_value


def test_handle_order_create_error_validation(payment_provider):
    """Test the response handler raises PayloadValidationError as expected"""
    r = json.loads("""{
        "result": 1,
        "type": "e-payment",
        "errors": ["Invalid auth code"]
    }""")
    with pytest.raises(PayloadValidationError):
        payment_provider.handle_order_create(r)


def test_handle_order_create_error_duplicate(payment_provider):
    """Test the response handler raises DuplicateOrderError as expected"""
    r = json.loads("""{
        "result": 2,
        "type": "e-payment"
    }""")
    with pytest.raises(DuplicateOrderError):
        payment_provider.handle_order_create(r)


def test_handle_order_create_error_unavailable(payment_provider):
    """Test the response handler raises ServiceUnavailableError as expected"""
    r = json.loads("""{
        "result": 10,
        "type": "e-payment"
    }""")
    with pytest.raises(ServiceUnavailableError):
        payment_provider.handle_order_create(r)


def test_handle_order_create_error_unknown_code(payment_provider):
    """Test the response handler raises UnknownReturnCodeError as expected"""
    r = json.loads("""{
        "result": 15,
        "type": "e-payment",
        "test": "unrecognized extra stuff"
    }""")
    with pytest.raises(UnknownReturnCodeError):
        payment_provider.handle_order_create(r)
