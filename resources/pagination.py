from rest_framework.pagination import PageNumberPagination
class DefaultPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'  # Allow client to override, using `?page_size=xxx
    max_page_size = 100
