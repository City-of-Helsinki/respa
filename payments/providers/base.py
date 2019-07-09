from typing import Optional
from urllib.parse import urlencode

from django.http import HttpRequest, HttpResponse, HttpResponseNotFound, HttpResponseServerError
from django.shortcuts import redirect
from django.urls import reverse

from ..models import Order

UI_RETURN_URL_PARAM_NAME = 'RESPA_UI_RETURN_URL'


class PaymentProvider:
    """Common base for payment provider integrations"""

    def __init__(self, **kwargs):
        if 'config' in kwargs:
            self.config = kwargs.get('config')
        self.request = kwargs.get('request')
        self.return_url = kwargs.get('return_url')

    def initiate_payment(self, order: Order) -> str:
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

    def get_success_url(self) -> str:
        return self.request.build_absolute_uri(reverse('payments:success'))

    def get_failure_url(self) -> str:
        return self.request.build_absolute_uri(reverse('payments:failure'))

    def get_notify_url(self) -> str:
        return self.request.build_absolute_uri(reverse('payments:notify'))

    def create_full_return_url(self) -> str:
        """Create the full URL where user is redirected after payment

        Can be overriden in subclass if the provider does not support
        adding extra query parameters into the return URL.
        """
        respa_return_url = self.get_success_url()
        query_params = urlencode({UI_RETURN_URL_PARAM_NAME: self.return_url})
        return '{}?{}'.format(respa_return_url, query_params)

    def extract_ui_return_url(self) -> str:
        """Parse and return where client is redirected after payment has been registered

        Can be overriden in subclass if the provider does not support
        the added extra query parameters in the return URL redirect.
        """
        return '' if not self.request else self.request.GET.get(UI_RETURN_URL_PARAM_NAME, '')

    @classmethod
    def ui_redirect_success(cls, return_url: str, order: Order = None) -> HttpResponse:
        """Redirect back to UI after a successful payment

        This should be used after a successful payment instead of the
        standard Django redirect.
        """
        return cls._redirect_to_ui(return_url, 'success', order) if return_url \
            else HttpResponse(content='Payment successful, but failed redirecting back to UI')

    @classmethod
    def ui_redirect_failure(cls, return_url: str, order: Order = None) -> HttpResponse:
        """Redirect back to UI after a failed payment

        This should be used after a failed payment instead of the
        standard Django redirect.
        """
        return cls._redirect_to_ui(return_url, 'failure', order) if return_url \
            else HttpResponseServerError(content='Payment failure and failed redirecting back to UI')

    @classmethod
    def _redirect_to_ui(cls, return_url: str, status: str, order: Optional[Order] = None):
        params = {'payment_status': status}
        if order:
            params['order_id'] = order.id
        return redirect('{}?{}'.format(return_url, urlencode(params)))
