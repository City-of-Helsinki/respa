
from django.urls import path, re_path
from django.conf.urls import include
from django.conf import settings

urlpatterns = [
    path(settings.MOUNT_PATH, include('respa.urls')),
]
