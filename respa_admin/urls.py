from django.conf.urls import url as unauthorized_url
from django.urls import include

from . import views
from .auth import admin_url as url
from .views.resources import (
    ManageUserPermissionsListView, ManageUserPermissionsSearchView, ManageUserPermissionsView, ResourceListView,
    SaveResourceView
)
from .views.units import UnitEditView, UnitListView

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
    url(r'^units/$', UnitListView.as_view(), name='units'),
    url(r'^units/edit/(?P<unit_id>[\w\d:]+)/$', UnitEditView.as_view(), name='edit-unit'),
    url(r'^i18n/$', include('django.conf.urls.i18n'), name='language'),
    url(r'^user_management/$', ManageUserPermissionsListView.as_view(), name='user-management'),
    url(r'^user_management/search/$', ManageUserPermissionsSearchView.as_view(), name='user-management-search'),
    url(r'^user_management/(?P<user_id>\w+)/$', ManageUserPermissionsView.as_view(), name='edit-user'),
]
