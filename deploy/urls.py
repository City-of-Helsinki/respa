
from django.urls import path
from django.conf.urls import include
from django.conf import settings

def trigger_error(request):
    division_by_zero = 1 / 0

urlpatterns = [
    path(settings.MOUNT_PATH, include('respa.urls')),
]

# If DEBUG_REQUEST is given, add view that sends Sentry report
if getattr(settings, 'DEBUG_REQUEST', False):
    urlpatterns = [path('sentry-debug/', trigger_error)] + urlpatterns
