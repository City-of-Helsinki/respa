"""respa URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.conf.urls import include, url
from django.contrib import admin
from rest_framework import routers

from resources.api import all_views as resources_views

router = routers.DefaultRouter()

registered_api_views = set()

for view in resources_views:
    kwargs = {}
    if view['name'] in registered_api_views:
        continue
    else:
        registered_api_views.add(view['name'])

    if 'base_name' in view:
        kwargs['base_name'] = view['base_name']
    router.register(view['name'], view['class'], **kwargs)


urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^v1/', include(router.urls)),
]
