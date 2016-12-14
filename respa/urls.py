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
from helusers import admin
from django.views.generic.base import RedirectView

from resources.api import RespaAPIRouter
from resources.views.images import ResourceImageView
from resources.views.ical import ICalFeedView
from resources.views import testing as testing_views

admin.autodiscover()

router = RespaAPIRouter()

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^accounts/', include('allauth.urls')),
    url(r'^grappelli/', include('grappelli.urls')),
    url(r'^resource_image/(?P<pk>\d+)$', ResourceImageView.as_view(), name='resource-image-view'),
    url(r'^v1/', include(router.urls)),
    url(r'^v1/reservation/ical/(?P<ical_token>[-\w\d]+).ics$', ICalFeedView.as_view(), name='ical-feed'),
    url(r'^$', RedirectView.as_view(url='v1/'))
]

if 'reports' in settings.INSTALLED_APPS:
    from reports.api import DailyReservationsReport
    urlpatterns.append(
        url(r'^reports/daily_reservations/', DailyReservationsReport.as_view(), name='daily-reservations-report')
    )


if settings.DEBUG:
    urlpatterns.append(
        url(r'test/availability$', testing_views.testing_view)
    )
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
