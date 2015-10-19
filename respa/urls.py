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
from django.conf import settings
from django.conf.urls.static import static

from rest_framework import routers

from resources.api import all_views as resources_views
from django.contrib.admin import site as admin_site
from resources.images import ResourceImageView

router = routers.DefaultRouter()

registered_api_views = set()

for view in resources_views:
    kwargs = {}
    if view['class'] in registered_api_views:
        continue
    else:
        registered_api_views.add(view['class'])

    if 'base_name' in view:
        kwargs['base_name'] = view['base_name']
    router.register(view['name'], view['class'], **kwargs)


urlpatterns = [
    url(r'^admin/', include(admin_site.urls)),
    url(r'^accounts/', include('allauth.urls')),
    url(r'^grappelli/', include('grappelli.urls')),
    url(r'^resource_image/(?P<pk>\d+)\.(?P<ext>[a-z]+)$', ResourceImageView.as_view(),
        name='resource-image-view'),
    url(r'^v1/', include(router.urls)),
]

if settings.DEBUG:
    urlpatterns.append(
        url(r'test/availability$', 'resources.views.testink')
    )
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
