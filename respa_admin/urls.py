from django.conf.urls import url as unauthorized_url

from . import views
from .views.resources import (
    RespaAdminIndex,
    ResourceListView,
    admin_office,
    SaveResourceView
)
from .auth import admin_url as url

urlpatterns = [
    url(r'^$', RespaAdminIndex.as_view(), name='index'),
    unauthorized_url(r'^login/$', views.login, name='respa-admin-login'),
    url(r'^resources/$', ResourceListView.as_view(), name='resources'),
    url(r'^resource/$', admin_form, name='resource'),
    url(r'^office/$', admin_office, name='office'),
    url(r'^resource/new/$', SaveResourceView.as_view(), name='new-resource'),
    url(r'^resource/edit/(?P<resource_id>\w+)/$', SaveResourceView.as_view(), name='edit-resource'),
]
