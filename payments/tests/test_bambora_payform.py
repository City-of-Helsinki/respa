import hmac
import json
from unittest import mock

import pytest
from django.http import HttpResponse, HttpResponseServerError
from django.test.client import RequestFactory
from requests.exceptions import RequestException
from rest_framework.reverse import reverse

from payments.models import Order
from payments.providers.bambora_payform import (
    RESPA_PAYMENTS_BAMBORA_API_KEY, BamboraPayformProvider, DuplicateOrderError, PayloadValidationError,
    ServiceUnavailableError, UnknownReturnCodeError
)

FAKE_BAMBORA_API_URL = "https://fake-bambora-api-url/api"
UI_RETURN_URL = 'https://front-end-url'
RESERVATION_LIST_URL = reverse('reservation-list')


@pytest.fixture(autouse=True)
def auto_use_django_db(db):
    pass


@pytest.fixture()
def provider_base_config():
    return {
        'RESPA_PAYMENTS_BAMBORA_API_URL': 'https://real-bambora-api-url/api',
        'RESPA_PAYMENTS_BAMBORA_API_KEY': 'dummy-key',
        'RESPA_PAYMENTS_BAMBORA_API_SECRET': 'dummy-secret',
        'RESPA_PAYMENTS_BAMBORA_PAYMENT_METHODS': ['dummy-bank']
    }


@pytest.fixture()
def payment_provider(provider_base_config):
    """When it doesn't matter if request is contained within provider the fixture can still be used"""
    return BamboraPayformProvider(config=provider_base_config)


def create_bambora_provider(provider_base_config, request, return_url=None):
    """Helper for creating a new instance of provider with request and optional return_url contained within"""
    return BamboraPayformProvider(config=provider_base_config,
                                  request=request,
                                  return_url=return_url)


def mocked_response_create(*args, **kwargs):
    """Mock Bambora auth token responses based on provider url"""
    class MockResponse:
        def __init__(self, data, status_code=200):
            self.json_data = data
            self.status_code = status_code

        def json(self):
            return self.json_data

        def raise_for_status(self):
            if self.status_code != 200:
                raise RequestException("Mock request error with status_code {}.".format(self.status_code))
            pass

    if args[0].startswith(FAKE_BAMBORA_API_URL):
        return MockResponse(data={}, status_code=500)
    else:
        return MockResponse(data={
            "result": 0,
            "token": "abc123",
            "type": "e-payment"
        })


def test_initiate_payment_success(provider_base_config, order_with_products):
    """Test the request creator constructs the payload base and returns a url that contains a token"""
    rf = RequestFactory()
    request = rf.post(RESERVATION_LIST_URL)

    payment_provider = create_bambora_provider(provider_base_config, request, UI_RETURN_URL)
    with mock.patch('payments.providers.bambora_payform.requests.post', side_effect=mocked_response_create):
        url = payment_provider.initiate_payment(order_with_products)
        assert url.startswith(payment_provider.url_payment_api)
        assert 'token' in url
        assert 'abc123' in url


def test_initiate_payment_error_unavailable(provider_base_config, order_with_products):
    """Test the request creator raises service unavailable if request doesn't go through"""
    rf = RequestFactory()
    request = rf.post(RESERVATION_LIST_URL)

    provider_base_config['RESPA_PAYMENTS_BAMBORA_API_URL'] = FAKE_BAMBORA_API_URL
    unavailable_payment_provider = create_bambora_provider(provider_base_config,
                                                           request, UI_RETURN_URL)

    with mock.patch('payments.providers.bambora_payform.requests.post', side_effect=mocked_response_create):
        with pytest.raises(ServiceUnavailableError):
            unavailable_payment_provider.initiate_payment(order_with_products)


def test_handle_initiate_payment_success(payment_provider):
    """Test the response handler recognizes success and adds token as part of the returned url"""
    r = json.loads("""{
        "result": 0,
        "token": "abc123",
        "type": "e-payment"
    }""")
    return_value = payment_provider.handle_initiate_payment(r)
    assert r['token'] in return_value


def test_handle_initiate_payment_error_validation(payment_provider):
    """Test the response handler raises PayloadValidationError as expected"""
    r = json.loads("""{
        "result": 1,
        "type": "e-payment",
        "errors": ["Invalid auth code"]
    }""")
    with pytest.raises(PayloadValidationError):
        payment_provider.handle_initiate_payment(r)


def test_handle_initiate_payment_error_duplicate(payment_provider):
    """Test the response handler raises DuplicateOrderError as expected"""
    r = json.loads("""{
        "result": 2,
        "type": "e-payment"
    }""")
    with pytest.raises(DuplicateOrderError):
        payment_provider.handle_initiate_payment(r)


def test_handle_initiate_payment_error_unavailable(payment_provider):
    """Test the response handler raises ServiceUnavailableError as expected"""
    r = json.loads("""{
        "result": 10,
        "type": "e-payment"
    }""")
    with pytest.raises(ServiceUnavailableError):
        payment_provider.handle_initiate_payment(r)


def test_handle_initiate_payment_error_unknown_code(payment_provider):
    """Test the response handler raises UnknownReturnCodeError as expected"""
    r = json.loads("""{
        "result": 15,
        "type": "e-payment",
        "test": "unrecognized extra stuff"
    }""")
    with pytest.raises(UnknownReturnCodeError):
        payment_provider.handle_initiate_payment(r)


def test_payload_add_products_success(payment_provider, order_with_products):
    """Test the products and total order price data is added correctly into payload"""
    payload = {}
    payment_provider.payload_add_products(payload, order_with_products)
    assert 'amount' in payload
    assert payload.get('amount') == 3720

    assert 'products' in payload
    products = payload.get('products')
    assert len(products) == 2
    # As there's no guaranteed order in nested dict, it's not possible
    # to check reliably for values, but at least assert that all keys are added
    for product in products:
        assert 'id' in product
        assert 'title' in product
        assert 'price' in product
        assert 'pretax_price' in product
        assert 'tax' in product
        assert 'count' in product
        assert 'type' in product


def test_payload_add_customer_success(payment_provider, order_with_products):
    """Test the customer data from order is added correctly into payload"""
    payload = {}
    payment_provider.payload_add_customer(payload, order_with_products)

    assert 'email' in payload
    assert payload.get('email') == 'test@example.com'

    assert 'customer' in payload
    customer = payload.get('customer')
    assert customer.get('firstname') == 'Seppo'
    assert customer.get('lastname') == 'Testi'
    assert customer.get('email') == 'test@example.com'
    assert customer.get('address_street') == 'Test street 1'
    assert customer.get('address_zip') == '12345'
    assert customer.get('address_city') == 'Testcity'


def test_payload_add_auth_code_success(payment_provider, order_with_products):
    """Test the auth code is added correctly into the payload"""
    payload = {
        'api_key': payment_provider.config.get(RESPA_PAYMENTS_BAMBORA_API_KEY),
        'order_number': order_with_products.order_number
    }
    payment_provider.payload_add_auth_code(payload)
    assert 'authcode' in payload


def test_calculate_auth_code_success(payment_provider):
    """Test the auth code calculation returns a correct hash"""
    data = 'dummy-key|abc123'
    calculated_code = payment_provider.calculate_auth_code(data)
    assert hmac.compare_digest(calculated_code, 'A8894068C4E17BFD55E68B2148CF555800773C673D19FA0648101C1E9CF5D0CE')


def test_check_new_payment_authcode_success(payment_provider):
    """Test the helper is able to extract necessary values from a request and compare authcodes"""
    params = {
        'RESPA_UI_RETURN_URL': 'http%3A%2F%2F127.0.0.1%3A8000%2Fv1',
        'AUTHCODE': '905EDAC01C9E6921250C21BE23CDC53633A4D66BE7241A3B5DA1D2372234D462',
        'RETURN_CODE': '0',
        'ORDER_NUMBER': 'abc123',
        'SETTLED': '1'
    }
    rf = RequestFactory()
    request = rf.get('/payments/success/', params)
    assert payment_provider.check_new_payment_authcode(request)


def test_check_new_payment_authcode_invalid(payment_provider):
    """Test the helper fails when params do not match the auth code"""
    params = {
        'RESPA_UI_RETURN_URL': 'http%3A%2F%2F127.0.0.1%3A8000%2Fv1',
        'AUTHCODE': '905EDAC01C9E6921250C21BE23CDC53633A4D66BE7241A3B5DA1D2372234D462',
        'RETURN_CODE': '0',
        'ORDER_NUMBER': 'abc123',
        'SETTLED': '0'
    }
    rf = RequestFactory()
    request = rf.get('/payments/success/', params)
    assert not payment_provider.check_new_payment_authcode(request)


def test_handle_success_request_return_url_missing(provider_base_config, order_with_products):
    """Test the handler returns a bad request object if return URL is missing from params"""
    params = {
        'AUTHCODE': '905EDAC01C9E6921250C21BE23CDC53633A4D66BE7241A3B5DA1D2372234D462',
        'RETURN_CODE': '0',
        'ORDER_NUMBER': 'abc123',
        'SETTLED': '0'
    }
    rf = RequestFactory()
    request = rf.get('/payments/success/', params)
    payment_provider = create_bambora_provider(provider_base_config, request, UI_RETURN_URL)

    returned = payment_provider.handle_success_request()
    assert isinstance(returned, HttpResponseServerError)
    assert returned.status_code == 500


def test_handle_success_request_order_not_found(provider_base_config, order_with_products):
    """Test request helper returns a failure url when order can't be found"""
    params = {
        'RESPA_UI_RETURN_URL': 'http%3A%2F%2F127.0.0.1%3A8000%2Fv1',
        'AUTHCODE': '83F6C12E8D894B433CB2B6A2A56709CF0AE26665768ED74FB28922F6ED128301',
        'RETURN_CODE': '0',
        'ORDER_NUMBER': 'abc567',
        'SETTLED': '1'
    }
    rf = RequestFactory()
    request = rf.get('/payments/success/', params)
    payment_provider = create_bambora_provider(provider_base_config, request, UI_RETURN_URL)
    returned = payment_provider.handle_success_request()
    assert isinstance(returned, HttpResponse)
    assert 'payment_status=failure' in returned.url


def test_handle_success_request_success(provider_base_config, order_with_products):
    """Test request helper changes the order status to confirmed

    Also check it returns a success url with order number"""
    params = {
        'RESPA_UI_RETURN_URL': 'http%3A%2F%2F127.0.0.1%3A8000%2Fv1',
        'AUTHCODE': '905EDAC01C9E6921250C21BE23CDC53633A4D66BE7241A3B5DA1D2372234D462',
        'RETURN_CODE': '0',
        'ORDER_NUMBER': 'abc123',
        'SETTLED': '1'
    }
    rf = RequestFactory()
    request = rf.get('/payments/success/', params)
    payment_provider = create_bambora_provider(provider_base_config, request, UI_RETURN_URL)
    returned = payment_provider.handle_success_request()
    order_after = Order.objects.get(order_number=params.get('ORDER_NUMBER'))
    assert order_after.state == Order.CONFIRMED
    assert isinstance(returned, HttpResponse)
    assert 'payment_status=success' in returned.url
    assert 'reservation_id={}'.format(order_after.reservation.id) in returned.url


def test_handle_success_request_payment_failed(provider_base_config, order_with_products):
    """Test request helper changes the order status to rejected and returns a failure url"""
    params = {
        'RESPA_UI_RETURN_URL': 'http%3A%2F%2F127.0.0.1%3A8000%2Fv1',
        'AUTHCODE': 'ED754E8F2E7FE0CC269B9F6A1C197F19B8393F37A1B63BE1E889D53F87A5FCA1',
        'RETURN_CODE': '1',
        'ORDER_NUMBER': 'abc123',
        'SETTLED': '1'
    }
    rf = RequestFactory()
    request = rf.get('/payments/success/', params)
    payment_provider = create_bambora_provider(provider_base_config, request, UI_RETURN_URL)
    returned = payment_provider.handle_success_request()
    order_after = Order.objects.get(order_number=params.get('ORDER_NUMBER'))
    assert order_after.state == Order.REJECTED
    assert isinstance(returned, HttpResponse)
    assert 'payment_status=failure' in returned.url


def test_handle_success_request_status_not_updated(provider_base_config, order_with_products):
    """Test request helper reacts to transaction status update error by returning a failure url"""
    params = {
        'RESPA_UI_RETURN_URL': 'http%3A%2F%2F127.0.0.1%3A8000%2Fv1',
        'AUTHCODE': 'D9170B2C0C0F36E467517E0DF2FC7D89BBC7237597B6BE3B0DE11518F93D7342',
        'RETURN_CODE': '4',
        'ORDER_NUMBER': 'abc123',
        'SETTLED': '1'
    }
    rf = RequestFactory()
    request = rf.get('/payments/success/', params)
    payment_provider = create_bambora_provider(provider_base_config, request, UI_RETURN_URL)
    returned = payment_provider.handle_success_request()
    # TODO Handling isn't final yet so there might be something extra that needs to be tested here
    assert isinstance(returned, HttpResponse)
    assert 'payment_status=failure' in returned.url


def test_handle_success_request_maintenance_break(provider_base_config, order_with_products):
    """Test request helper reacts to maintenance break error by returning a failure url"""
    params = {
        'RESPA_UI_RETURN_URL': 'http%3A%2F%2F127.0.0.1%3A8000%2Fv1',
        'AUTHCODE': '144662CEBD9861D4526C4147D10FB6C50FE1E02453701F8972B699CFD1F4A99E',
        'RETURN_CODE': '10',
        'ORDER_NUMBER': 'abc123',
        'SETTLED': '1'
    }
    rf = RequestFactory()
    request = rf.get('/payments/success/', params)
    payment_provider = create_bambora_provider(provider_base_config, request, UI_RETURN_URL)
    returned = payment_provider.handle_success_request()
    # TODO Handling isn't final yet so there might be something extra that needs to be tested here
    assert isinstance(returned, HttpResponse)
    assert 'payment_status=failure' in returned.url


def test_handle_success_request_unknown_error(provider_base_config, order_with_products):
    """Test request helper returns a failure url when status code is unknown"""
    params = {
        'RESPA_UI_RETURN_URL': 'http%3A%2F%2F127.0.0.1%3A8000%2Fv1',
        'AUTHCODE': '3CD17A51E89C0A6DDDCA743AFCBD5DC40E8FF8AB97756089E75EC953A19A938C',
        'RETURN_CODE': '15',
        'ORDER_NUMBER': 'abc123',
        'SETTLED': '1'
    }
    rf = RequestFactory()
    request = rf.get('/payments/success/', params)
    payment_provider = create_bambora_provider(provider_base_config, request, UI_RETURN_URL)
    returned = payment_provider.handle_success_request()
    assert isinstance(returned, HttpResponse)
    assert 'payment_status=failure' in returned.url


def test_handle_notify_request_order_not_found(provider_base_config, order_with_products):
    """Test request notify helper returns http 204 when order can't be found"""
    params = {
        'RESPA_UI_RETURN_URL': 'http%3A%2F%2F127.0.0.1%3A8000%2Fv1',
        'AUTHCODE': '83F6C12E8D894B433CB2B6A2A56709CF0AE26665768ED74FB28922F6ED128301',
        'RETURN_CODE': '0',
        'ORDER_NUMBER': 'abc567',
        'SETTLED': '1'
    }
    rf = RequestFactory()
    request = rf.get('/payments/notify/', params)
    payment_provider = create_bambora_provider(provider_base_config, request, UI_RETURN_URL)
    returned = payment_provider.handle_notify_request()
    assert isinstance(returned, HttpResponse)
    assert returned.status_code == 204


@pytest.mark.parametrize('order_state, expected_order_state', (
    (Order.WAITING, Order.CONFIRMED),
    (Order.CONFIRMED, Order.CONFIRMED),
    (Order.EXPIRED, Order.EXPIRED),
    (Order.REJECTED, Order.REJECTED),
))
def test_handle_notify_request_success(provider_base_config, order_with_products, order_state, expected_order_state):
    """Test request notify helper returns http 204 and order status is correct when successful"""
    params = {
        'RESPA_UI_RETURN_URL': 'http%3A%2F%2F127.0.0.1%3A8000%2Fv1',
        'AUTHCODE': '905EDAC01C9E6921250C21BE23CDC53633A4D66BE7241A3B5DA1D2372234D462',
        'RETURN_CODE': '0',
        'ORDER_NUMBER': 'abc123',
        'SETTLED': '1'
    }
    order_with_products.set_state(order_state)

    rf = RequestFactory()
    request = rf.get('/payments/notify/', params)
    payment_provider = create_bambora_provider(provider_base_config, request, UI_RETURN_URL)
    returned = payment_provider.handle_notify_request()
    order_after = Order.objects.get(order_number=params.get('ORDER_NUMBER'))
    assert order_after.state == expected_order_state
    assert isinstance(returned, HttpResponse)
    assert returned.status_code == 204


@pytest.mark.parametrize('order_state, expected_order_state', (
    (Order.WAITING, Order.REJECTED),
    (Order.REJECTED, Order.REJECTED),
    (Order.EXPIRED, Order.EXPIRED),
    (Order.CONFIRMED, Order.CONFIRMED),
))
def test_handle_notify_request_payment_failed(provider_base_config, order_with_products, order_state,
                                              expected_order_state):
    """Test request notify helper returns http 204 and order status is correct when payment fails"""
    params = {
        'RESPA_UI_RETURN_URL': 'http%3A%2F%2F127.0.0.1%3A8000%2Fv1',
        'AUTHCODE': 'ED754E8F2E7FE0CC269B9F6A1C197F19B8393F37A1B63BE1E889D53F87A5FCA1',
        'RETURN_CODE': '1',
        'ORDER_NUMBER': 'abc123',
        'SETTLED': '1'
    }
    order_with_products.set_state(order_state)

    rf = RequestFactory()
    request = rf.get('/payments/notify/', params)
    payment_provider = create_bambora_provider(provider_base_config, request, UI_RETURN_URL)
    returned = payment_provider.handle_notify_request()
    order_after = Order.objects.get(order_number=params.get('ORDER_NUMBER'))
    assert order_after.state == expected_order_state
    assert isinstance(returned, HttpResponse)
    assert returned.status_code == 204


def test_handle_notify_request_unknown_error(provider_base_config, order_with_products):
    """Test request notify helper returns http 204 when status code is unknown"""
    params = {
        'RESPA_UI_RETURN_URL': 'http%3A%2F%2F127.0.0.1%3A8000%2Fv1',
        'AUTHCODE': '3CD17A51E89C0A6DDDCA743AFCBD5DC40E8FF8AB97756089E75EC953A19A938C',
        'RETURN_CODE': '15',
        'ORDER_NUMBER': 'abc123',
        'SETTLED': '1'
    }
    rf = RequestFactory()
    request = rf.get('/payments/notify/', params)
    payment_provider = create_bambora_provider(provider_base_config, request, UI_RETURN_URL)
    returned = payment_provider.handle_notify_request()
    assert isinstance(returned, HttpResponse)
    assert returned.status_code == 204
