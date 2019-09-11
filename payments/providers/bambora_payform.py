import hashlib
import hmac
import logging

import requests
from django.http import HttpResponse
from requests.exceptions import RequestException

from ..exceptions import (
    DuplicateOrderError, OrderStateTransitionError, PayloadValidationError, ServiceUnavailableError,
    UnknownReturnCodeError
)
from ..models import Order, OrderLine
from ..utils import price_as_sub_units
from .base import PaymentProvider

logger = logging.getLogger(__name__)

# Keys the provider expects to find in the config
RESPA_PAYMENTS_BAMBORA_API_URL = 'RESPA_PAYMENTS_BAMBORA_API_URL'
RESPA_PAYMENTS_BAMBORA_API_KEY = 'RESPA_PAYMENTS_BAMBORA_API_KEY'
RESPA_PAYMENTS_BAMBORA_API_SECRET = 'RESPA_PAYMENTS_BAMBORA_API_SECRET'
RESPA_PAYMENTS_BAMBORA_PAYMENT_METHODS = 'RESPA_PAYMENTS_BAMBORA_PAYMENT_METHODS'


class BamboraPayformProvider(PaymentProvider):
    """Bambora Payform specific integration utilities and configuration
    testing docs: https://payform.bambora.com/docs/web_payments/?page=testing
    api reference: https://payform.bambora.com/docs/web_payments/?page=full-api-reference
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.url_payment_api = self.config.get(RESPA_PAYMENTS_BAMBORA_API_URL)
        self.url_payment_auth = '{}/auth_payment'.format(self.url_payment_api)
        self.url_payment_token = '{}/token/{{token}}'.format(self.url_payment_api)

    @staticmethod
    def get_config_template() -> dict:
        """Keys and value types what Bambora requires from environment"""
        return {
            RESPA_PAYMENTS_BAMBORA_API_URL: (str, 'https://payform.bambora.com/pbwapi'),
            RESPA_PAYMENTS_BAMBORA_API_KEY: str,
            RESPA_PAYMENTS_BAMBORA_API_SECRET: str,
            RESPA_PAYMENTS_BAMBORA_PAYMENT_METHODS: list
        }

    def initiate_payment(self, order) -> str:
        """Initiate payment by constructing the payload with necessary items"""

        payload = {
            'version': 'w3.1',
            'api_key': self.config.get(RESPA_PAYMENTS_BAMBORA_API_KEY),
            'payment_method': {
                'type': 'e-payment',
                'return_url': self.get_success_url(),
                'notify_url': self.get_notify_url(),
                'selected': self.config.get(RESPA_PAYMENTS_BAMBORA_PAYMENT_METHODS)
            },
            'currency': 'EUR',
            'order_number': str(order.order_number)
        }

        self.payload_add_products(payload, order)
        self.payload_add_customer(payload, order)
        self.payload_add_auth_code(payload)

        try:
            r = requests.post(self.url_payment_auth, json=payload, timeout=60)
            r.raise_for_status()
            return self.handle_initiate_payment(r.json())
        except RequestException as e:
            raise ServiceUnavailableError("Payment service is unreachable") from e

    def handle_initiate_payment(self, response) -> str:
        """Handling the Bambora payment auth response"""
        result = response['result']
        if result == 0:
            # Create the URL where user is redirected to complete the payment
            # Append "?minified" to get a stripped version of the payment page
            return self.url_payment_token.format(token=response['token'])
        elif result == 1:
            raise PayloadValidationError("Payment payload data validation failed: {}"
                                         .format(" ".join(response['errors'])))
        elif result == 2:
            raise DuplicateOrderError("Order with the same ID already exists")
        elif result == 10:
            raise ServiceUnavailableError("Payment service is down for maintentance")
        else:
            raise UnknownReturnCodeError("Return code was not recognized: {}".format(result))

    def payload_add_products(self, payload, order):
        """Attach info of bought products to payload

        Order lines that contain bought products are retrieved through order"""
        reservation = order.reservation
        order_lines = OrderLine.objects.filter(order=order.id)
        items = []
        for order_line in order_lines:
            product = order_line.product
            int_tax = int(product.tax_percentage)
            assert int_tax == product.tax_percentage  # make sure the tax is a whole number
            items.append({
                'id': product.sku,
                'title': product.name,
                'price': price_as_sub_units(product.get_price_for_reservation(reservation)),
                'pretax_price': price_as_sub_units(product.get_pretax_price_for_reservation(reservation)),
                'tax': int_tax,
                'count': order_line.quantity,
                'type': 1
            })
        payload['amount'] = price_as_sub_units(order.get_price())
        payload['products'] = items

    def payload_add_customer(self, payload, order):
        """Attach customer data to payload"""
        reservation = order.reservation
        payload.update({
            'email': reservation.billing_email_address,
            'customer': {
                'firstname': reservation.billing_first_name,
                'lastname': reservation.billing_last_name,
                'email': reservation.billing_email_address,
                'address_street': reservation.billing_address_street,
                'address_zip': reservation.billing_address_zip,
                'address_city': reservation.billing_address_city,
            }
        })

    def payload_add_auth_code(self, payload):
        """Construct auth code string and hash it into payload"""
        data = '{}|{}'.format(payload['api_key'], payload['order_number'])
        payload.update(authcode=self.calculate_auth_code(data))

    def calculate_auth_code(self, data) -> str:
        """Calculate a hmac sha256 out of some data string"""
        return hmac.new(bytes(self.config.get(RESPA_PAYMENTS_BAMBORA_API_SECRET), 'latin-1'),
                        msg=bytes(data, 'latin-1'),
                        digestmod=hashlib.sha256).hexdigest().upper()

    def check_new_payment_authcode(self, request):
        """Validate that success/notify payload authcode matches"""
        is_valid = True
        auth_code_calculation_values = [
            request.GET[param_name]
            for param_name in ('RETURN_CODE', 'ORDER_NUMBER', 'SETTLED', 'CONTACT_ID', 'INCIDENT_ID')
            if param_name in request.GET
        ]
        correct_auth_code = self.calculate_auth_code('|'.join(auth_code_calculation_values))
        auth_code = request.GET['AUTHCODE']
        if not hmac.compare_digest(auth_code, correct_auth_code):
            logger.warning('Incorrect auth code "{}".'.format(auth_code))
            is_valid = False
        return is_valid

    def handle_success_request(self):  # noqa: C901
        """Handle the payform response after user has completed the payment flow in normal fashion"""
        request = self.request
        logger.debug('Handling Bambora user return request, params: {}.'.format(request.GET))

        if not self.check_new_payment_authcode(request):
            return self.ui_redirect_failure()

        try:
            order = Order.objects.get(order_number=request.GET['ORDER_NUMBER'])
        except Order.DoesNotExist:
            logger.warning('Order does not exist.')
            return self.ui_redirect_failure()

        return_code = request.GET['RETURN_CODE']
        if return_code == '0':
            logger.debug('Payment completed successfully.')
            try:
                order.set_state(Order.CONFIRMED, 'Code 0 (payment succeeded) in Bambora Payform success request.')
                return self.ui_redirect_success(order)
            except OrderStateTransitionError as oste:
                logger.warning(oste)
                order.create_log_entry('Code 0 (payment succeeded) in Bambora Payform success request.')
                return self.ui_redirect_failure(order)
        elif return_code == '1':
            logger.debug('Payment failed.')
            try:
                order.set_state(Order.REJECTED, 'Code 1 (payment rejected) in Bambora Payform success request.')
                return self.ui_redirect_failure(order)
            except OrderStateTransitionError as oste:
                logger.warning(oste)
                order.create_log_entry('Code 1 (payment rejected) in Bambora Payform success request.')
                return self.ui_redirect_failure(order)
        elif return_code == '4':
            logger.debug('Transaction status could not be updated.')
            order.create_log_entry(
                'Code 4: Transaction status could not be updated. Use the merchant UI to resolve.'
            )
            return self.ui_redirect_failure(order)
        elif return_code == '10':
            logger.debug('Maintenance break.')
            order.create_log_entry('Code 10: Bambora Payform maintenance break')
            return self.ui_redirect_failure(order)
        else:
            logger.warning('Incorrect RETURN_CODE "{}".'.format(return_code))
            order.create_log_entry('Bambora Payform incorrect return code "{}".'.format(return_code))
            return self.ui_redirect_failure(order)

    def handle_notify_request(self):
        """Handle the asynchronous part of payform response

        Arrives some time after user has completed the payment flow or stopped it abruptly.
        Skips changing order state if it has been previously set. Although, according to
        Bambora's documentation, there are some cases where payment state might change
        from failed to successful, the reservation has probably been soft-cleaned up by then.
        TODO Maybe try recreating the reservation if the time slot is still available

        Bambora expects 20x response to acknowledge the notify was received"""
        request = self.request
        logger.debug('Handling Bambora notify request, params: {}.'.format(request.GET))

        if not self.check_new_payment_authcode(request):
            return HttpResponse(status=204)

        try:
            order = Order.objects.get(order_number=request.GET['ORDER_NUMBER'])
        except Order.DoesNotExist:
            # Target order might be deleted after posting but before the notify arrives
            logger.warning('Notify: Order does not exist.')
            return HttpResponse(status=204)

        return_code = request.GET['RETURN_CODE']
        if return_code == '0':
            logger.debug('Notify: Payment completed successfully.')
            try:
                order.set_state(Order.CONFIRMED, 'Code 0 (payment succeeded) in Bambora Payform notify request.')
            except OrderStateTransitionError as oste:
                logger.warning(oste)
        elif return_code == '1':
            logger.debug('Notify: Payment failed.')
            try:
                order.set_state(Order.REJECTED, 'Code 1 (payment rejected) in Bambora Payform notify request.')
            except OrderStateTransitionError as oste:
                logger.warning(oste)
        else:
            logger.debug('Notify: Incorrect RETURN_CODE "{}".'.format(return_code))

        return HttpResponse(status=204)
