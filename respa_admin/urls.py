from django.conf.urls import include, url

from .views.resources import (
    admin_index,
    ResourceListView,
    admin_form,
    admin_office,
    SaveResourceView
)

urlpatterns = [
    url(r'^$', admin_index, name='index'),
    url(r'^resources/$', ResourceListView.as_view(), name='resources'),
    url(r'^resource/$', admin_form, name='resource'),
    url(r'^office/$', admin_office, name='office'),
    url(r'^form/$', admin_form, name='form'),
    url(r'^resource/new/$', SaveResourceView.as_view(), name='new-resource'),
    url(r'^resource/edit/(?P<resource_id>\w+)/$', SaveResourceView.as_view(), name='edit-resource'),
]
