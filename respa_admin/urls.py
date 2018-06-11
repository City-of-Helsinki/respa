from django.conf.urls import url as unauthorized_url

from . import views
from .views.resources import (
    admin_index,
    ResourceListView,
    admin_form,
    admin_office,
    SaveResourceView
)
from .auth import admin_url as url

urlpatterns = [
    unauthorized_url(r'^login/$', views.login, name='respa-admin-login'),
    url(r'^$', admin_index, name='index'),
    url(r'^resources/$', ResourceListView.as_view(), name='resources'),
    url(r'^resource/$', admin_form, name='resource'),
    url(r'^office/$', admin_office, name='office'),
    url(r'^form/$', admin_form, name='form'),
    url(r'^resource/new/$', SaveResourceView.as_view(), name='new-resource'),
    url(r'^resource/edit/(?P<resource_id>\w+)/$', SaveResourceView.as_view(), name='edit-resource'),
]
