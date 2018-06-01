from django.conf.urls import include, url

from . import views

urlpatterns = [
    url(r'^$', views.admin_index, name='index'),
    url(r'^resources/$', views.ResourceListView.as_view(), name='resources'),
]
