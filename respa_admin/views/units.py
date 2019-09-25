from django.db.models import FieldDoesNotExist
from django.views.generic import ListView
from resources.models import Unit
from respa_admin.views.base import ExtraContextMixin


class UnitListView(ExtraContextMixin, ListView):
    model = Unit
    paginate_by = 10
    context_object_name = 'units'
    template_name = 'respa_admin/page_units.html'

    def get(self, request, *args, **kwargs):
        get_params = request.GET
        self.search_query = get_params.get('search_query')
        self.order_by = get_params.get('order_by', 'name')
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context['search_query'] = self.search_query or ''
        context['order_by'] = self.order_by
        return context

    def get_managed_units_queryset(self):
        qs = super().get_queryset()
        qs = qs.managed_by(self.request.user)
        return qs

    def get_queryset(self):
        qs = self.get_managed_units_queryset()

        if self.search_query:
            qs = qs.filter(name__icontains=self.search_query)
        if self.order_by:
            order_by_param = self.order_by.strip('-')
            try:
                if Unit._meta.get_field(order_by_param):
                    qs = qs.order_by(self.order_by)
            except FieldDoesNotExist:
                pass
        return qs
