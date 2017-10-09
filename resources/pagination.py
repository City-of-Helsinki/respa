from rest_framework.pagination import PageNumberPagination, _positive_int


class DefaultPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'  # Allow client to override, using `?page_size=xxx
    max_page_size = 500


class PurposePagination(DefaultPagination):
    page_size = 40


class ReservationPagination(DefaultPagination):
    def get_page_size(self, request):
        if self.page_size_query_param:
            cutoff = self.max_page_size
            if request.query_params.get('format', '').lower() == 'xlsx':
                cutoff = 50000
            try:
                return _positive_int(
                    request.query_params[self.page_size_query_param],
                    strict=True, cutoff=cutoff
                )
            except (KeyError, ValueError):
                pass

        return self.page_size
