from django.conf.urls import include, url

from . import views

urlpatterns = [
    url(r'^$', views.admin_index, name='index'),
    url(r'^resources/$', views.ResourceListView.as_view(), name='resources'),
    url(r'^resource/$', views.admin_resource, name='resource'),
    url(r'^office/$', views.admin_office, name='office'),
    url(r'^form/$', views.admin_form, name='form')
]
