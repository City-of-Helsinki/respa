from collections import namedtuple

from django.http import HttpRequest, HttpResponse, HttpResponseNotFound
from django.shortcuts import redirect
from django.urls import reverse

from payments import settings

PurchasedItem = namedtuple('PurchasedItem',
                           'id, title, price, pretax_price, tax count type')

Customer = namedtuple('Customer',
                      'firstname lastname email address_street address_zip address_city')


class PaymentsBase(object):
    """Common base for payment provider integrations"""

    def __init__(self, **kwargs):
        self.api_key = settings.PAYMENT_API_KEY
        self.api_secret = settings.PAYMENT_API_SECRET
        self.url_api = settings.PAYMENT_URL_API

    def order_post(self):
        raise NotImplementedError

    def get_customer(self):
        raise NotImplementedError

    def get_purchased_items(self):
        return []

    def calculate_auth_code(self, data):
        """Calculate and return a hash of some data

        As the hashing algorithms and data varies between providers
        there needs to be a subclass implementation"""
        raise NotImplementedError

    def handle_success_request(self, request: HttpRequest) -> HttpResponse:
        """Handle incoming payment success request from the payment provider.

        Implement this in your subclass. If everything goes smoothly, should
        redirect the client back to the UI return URL."""
        raise NotImplementedError

    def handle_failure_request(self, request: HttpRequest) -> HttpResponse:
        """Handle incoming payment failure request from the payment provider.

        Override this in your subclass if you need to handle failure requests.
        When everything goes smoothly, should redirect the client back to the
        UI return URL."""
        return HttpResponseNotFound()

    def handle_notify_request(self, request: HttpRequest) -> HttpResponse:
        """Handle incoming notify request from the payment provider.

        Override this in your subclass if you need to handle notify requests."""
        return HttpResponseNotFound()

    def get_success_url(self, request: HttpRequest) -> str:
        return request.build_absolute_uri(reverse('payments:success'))

    def get_failure_url(self, request: HttpRequest) -> str:
        return request.build_absolute_uri(reverse('payments:failure'))

    def get_notify_url(self, request: HttpRequest) -> str:
        return request.build_absolute_uri(reverse('payments:notify'))

    @classmethod
    def ui_redirect_success(cls, return_url: str) -> HttpResponse:
        """Redirect back to UI after a successful payment

        This should be used after a successful payment instead of the
        standard Django redirect.
        """
        return redirect('{}?status=success'.format(return_url))

    @classmethod
    def ui_redirect_failure(cls, return_url: str) -> HttpResponse:
        """Redirect back to UI after a failed payment

        This should be used after a failed payment instead of the
        standard Django redirect.
        """
        return redirect('{}?status=failure'.format(return_url))


class PaymentError(Exception):
    """Base for payment specific exceptions"""
