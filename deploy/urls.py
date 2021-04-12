
from django.urls import path
from django.conf.urls import include
from django.conf import settings

urlpatterns = [
    path(settings.MOUNT_PATH, include('respa.urls')),
]
