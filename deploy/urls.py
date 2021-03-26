
from django.urls import path, re_path
from django.conf.urls import include

urlpatterns = [
    path('', include('respa.urls')),
]
