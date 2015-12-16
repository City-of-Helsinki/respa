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
from django.contrib.admin import site as admin_site
from django.utils.translation import ugettext_lazy

from resources.api import RespaAPIRouter
from resources.views.images import ResourceImageView
from resources.views.ical import ICalFeedView

# Text to put at the end of each page's <title>.
admin_site.site_title = ugettext_lazy('RESPA Resource booking system')

# Text to put in each page's <h1>.
admin_site.site_header = ugettext_lazy('RESPA Resource booking system')

# Text to put at the top of the admin index page.
admin_site.index_title = ugettext_lazy('RESPA Administration')

router = RespaAPIRouter()

urlpatterns = [
    url(r'^admin/', include(admin_site.urls)),
    url(r'^accounts/', include('allauth.urls')),
    url(r'^grappelli/', include('grappelli.urls')),
    url(r'^resource_image/(?P<pk>\d+)$', ResourceImageView.as_view(), name='resource-image-view'),
    url(r'^v1/', include(router.urls)),
    url(r'^v1/reservation/ical/(?P<ical_token>[-\w\d]+).ics$', ICalFeedView.as_view(), name='ical-feed'),
]

if settings.DEBUG:
    urlpatterns.append(
        url(r'test/availability$', 'resources.views.testing.testing_view')
    )
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
