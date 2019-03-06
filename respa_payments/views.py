from django.db.models import Sum
from django.views.generic import ListView
from respa_payments.models import Order


class PaymentListView(ListView):
    model = Order
    paginate_by = 10
    context_object_name = 'payments'
    template_name = 'respa_payments/page_payments.html'

    def get_context_data(self, **kwargs):
        context = super(PaymentListView, self).get_context_data()
        context['total_payment_service_amount'] = str(Order.objects.aggregate(
          Sum('payment_service_amount')
        )['payment_service_amount__sum'])
        return context
