from django.urls import path

from .views import FailureView, notify_view, SuccessView


app_name = 'payments'

urlpatterns = [
    path('success/', SuccessView.as_view(), name='success'),
    path('failure/', FailureView.as_view(), name='failure'),
    path('notify/', notify_view, name='notify'),

]
