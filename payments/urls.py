from django.urls import path

from .views import FailureView, SuccessView, notify_view

app_name = 'payments'

urlpatterns = [
    path('success/', SuccessView.as_view(), name='success'),
    path('failure/', FailureView.as_view(), name='failure'),
    path('notify/', notify_view, name='notify'),

]
