from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .providers import get_payment_provider


class SuccessView(View):
    def get(self, request):
        return get_payment_provider().handle_success_request(request)


class FailureView(View):
    def get(self, request):
        return get_payment_provider().handle_failure_request(request)


@csrf_exempt
def notify_view(request):
    return get_payment_provider().handle_notify_request(request)
