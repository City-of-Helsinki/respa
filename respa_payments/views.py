from django.db.models import Sum
from django.views.generic import ListView
from respa_payments.models import Order
import datetime


class PaymentListView(ListView):
    model = Order
    paginate_by = 30
    context_object_name = 'payments'
    template_name = 'respa_payments/page_payments.html'

    def get(self, request, *args, **kwargs):
        get_params = request.GET
        self.filter_start = get_params.get('filter_start')
        self.filter_end = get_params.get('filter_end')
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(PaymentListView, self).get_context_data()
        context['total_payment_service_amount'] = str(self.get_queryset().aggregate(
          Sum('payment_service_amount')
        )['payment_service_amount__sum'])
        context['filter_start'] = self.filter_start
        context['filter_end'] = self.filter_end
        return context

    def get_queryset(self):
        qs = super(PaymentListView, self).get_queryset()
        if self.filter_start:
            qs = qs.filter(order_process_started__gte=datetime.datetime.strptime(self.filter_start, '%d.%m.%Y'))
        if self.filter_end:
            qs = qs.filter(order_process_started__lte=datetime.datetime.strptime(self.filter_end, '%d.%m.%Y')
                           + datetime.timedelta(days=1))
        return qs
