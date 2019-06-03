from typing import Optional
from urllib.parse import urlencode

from django.http import HttpRequest, HttpResponse, HttpResponseNotFound
from django.shortcuts import redirect
from django.urls import reverse

from ..models import Order

PAYMENT_CONFIG = 'PAYMENT_CONFIG'


class PaymentProvider:
    """Common base for payment provider integrations"""

    def __init__(self, **kwargs):
        self.config = kwargs.get(PAYMENT_CONFIG)

    def order_create(self, request: HttpRequest, ui_return_url: str, order: Order) -> str:
        """Create a payment to the provider.

        Implement this in your subclass. Should return a URL to which the user
        is redirected to actually pay the order."""

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
    def ui_redirect_success(cls, return_url: str, order: Order = None) -> HttpResponse:
        """Redirect back to UI after a successful payment

        This should be used after a successful payment instead of the
        standard Django redirect.
        """
        return cls._redirect_to_ui(return_url, 'success', order)

    @classmethod
    def ui_redirect_failure(cls, return_url: str, order: Order = None) -> HttpResponse:
        """Redirect back to UI after a failed payment

        This should be used after a failed payment instead of the
        standard Django redirect.
        """
        return cls._redirect_to_ui(return_url, 'failure', order)

    @classmethod
    def _redirect_to_ui(cls, return_url: str, status: str, order: Optional[Order] = None):
        params = {'payment_status': status}
        if order:
            params['order_id'] = order.id
        return redirect('{}?{}'.format(return_url, urlencode(params)))


class PaymentError(Exception):
    """Base for payment specific exceptions"""
