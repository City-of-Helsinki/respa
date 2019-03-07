from django.conf.urls import url as unauthorized_url
from django.urls import include

from . import views
from .views.resources import (
    ResourceListView,
    SaveResourceView
)
from .auth import admin_url as url

app_name = 'respa_admin'
urlpatterns = [
    url(r'^$', ResourceListView.as_view(), name='index'),
    unauthorized_url(r'^login/$', views.LoginView.as_view(), name='login'),
    unauthorized_url(r'^login/tunnistamo/$',
                     views.tunnistamo_login, name='tunnistamo-login'),
    unauthorized_url(r'^logout/$', views.logout, name='logout'),
    url(r'^resources/$', ResourceListView.as_view(), name='resources'),
    url(r'^resource/new/$', SaveResourceView.as_view(), name='new-resource'),
    url(r'^resource/edit/(?P<resource_id>\w+)/$', SaveResourceView.as_view(), name='edit-resource'),
    url(r'^i18n/$', include('django.conf.urls.i18n'), name='language'),
]
