from urllib.parse import urlencode

from django.http import HttpResponse, HttpResponseNotFound, HttpResponseServerError
from django.shortcuts import redirect
from django.urls import reverse

from ..models import Order


class PaymentProvider:
    """Common base for payment provider integrations"""
    ui_return_url_param_name = 'RESPA_UI_RETURN_URL'

    def __init__(self, **kwargs):
        if 'config' in kwargs:
            self.config = kwargs.get('config')
        self.request = kwargs.get('request')
        self.ui_return_url = kwargs.get('ui_return_url')

    def initiate_payment(self, order: Order) -> str:
        """Create a payment to the provider.

        Implement this in your subclass. Should return a URL to which the user
        is redirected to actually pay the order."""

    def handle_success_request(self) -> HttpResponse:
        """Handle incoming payment success request from the payment provider.

        Implement this in your subclass. If everything goes smoothly, should
        redirect the client back to the UI return URL."""
        raise NotImplementedError

    def handle_failure_request(self) -> HttpResponse:
        """Handle incoming payment failure request from the payment provider.

        Override this in your subclass if you need to handle failure requests.
        When everything goes smoothly, should redirect the client back to the
        UI return URL."""
        return HttpResponseNotFound()

    def handle_notify_request(self) -> HttpResponse:
        """Handle incoming notify request from the payment provider.

        Override this in your subclass if you need to handle notify requests."""
        return HttpResponseNotFound()

    def get_success_url(self) -> str:
        """Create the full URL where user is redirected after a successful payment

        By default adds the UI return URL to the final URL as a query
        parameter. If the provider does not support that, you should
        use get_respa_success_url() instead, override extract_ui_return_url()
        and handle the UI return URL yourself.
        """
        return self._get_final_return_url(self.get_respa_success_url())

    def get_failure_url(self) -> str:
        """Create the full URL where user is redirected after a failed payment

        By default adds the UI return URL to the final URL as a query
        parameter. If the provider does not support that, you should
        use get_respa_failure_url() instead, override extract_ui_return_url()
        and handle the UI return URL yourself.
        """
        return self._get_final_return_url(self.get_respa_failure_url())

    def get_notify_url(self) -> str:
        return self.request.build_absolute_uri(reverse('payments:notify'))

    def get_respa_success_url(self) -> str:
        return self.request.build_absolute_uri(reverse('payments:success'))

    def get_respa_failure_url(self) -> str:
        return self.request.build_absolute_uri(reverse('payments:failure'))

    def extract_ui_return_url(self) -> str:
        """Parse and return where client is redirected after payment has been registered

        Can be overriden in subclass if the provider does not support
        the added extra query parameters in the return URL redirect.
        """
        return '' if not self.request else self.request.GET.get(self.ui_return_url_param_name, '')

    def ui_redirect_success(self, order: Order = None) -> HttpResponse:
        """Redirect back to UI after a successful payment

        This should be used after a successful payment instead of the
        standard Django redirect.
        """
        ui_return_url = self.extract_ui_return_url()
        if ui_return_url:
            return self._redirect_to_ui(ui_return_url, 'success', order)
        else:
            return HttpResponse(content='Payment successful, but failed redirecting back to UI')

    def ui_redirect_failure(self, order: Order = None) -> HttpResponse:
        """Redirect back to UI after a failed payment

        This should be used after a failed payment instead of the
        standard Django redirect.
        """
        ui_return_url = self.extract_ui_return_url()
        if ui_return_url:
            return self._redirect_to_ui(ui_return_url, 'failure', order)
        else:
            return HttpResponseServerError(content='Payment failure and failed redirecting back to UI')

    def _get_final_return_url(self, respa_return_url):
        query_params = urlencode({self.ui_return_url_param_name: self.ui_return_url})
        return '{}?{}'.format(respa_return_url, query_params)

    @classmethod
    def _redirect_to_ui(cls, return_url: str, status: str, order: Order = None):
        params = {'payment_status': status}
        if order:
            params['reservation_id'] = order.reservation_id
        return redirect('{}?{}'.format(return_url, urlencode(params)))
