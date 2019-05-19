from django.urls import path, re_path
from django.conf.urls import include
from django.conf import settings
from django.conf.urls.static import static
from helusers import admin
from django.views.generic.base import RedirectView

from resources.api import RespaAPIRouter
from resources.views.images import ResourceImageView
from resources.views.ical import ICalFeedView

admin.autodiscover()

if getattr(settings, 'RESPA_COMMENTS_ENABLED', False):
    import comments.api

if getattr(settings, 'RESPA_CATERINGS_ENABLED', False):
    import caterings.api

router = RespaAPIRouter()

urlpatterns = [
    path('admin/', admin.site.urls),
    path('ra/', include('respa_admin.urls', namespace='respa_admin')),
    path('i18n/', include('django.conf.urls.i18n')),
    path('accounts/', include('allauth.urls')),
    path('grappelli/', include('grappelli.urls')),
    path('resource_image/<int:pk>', ResourceImageView.as_view(), name='resource-image-view'),
    path('v1/', include(router.urls)),
    re_path(r'v1/reservation/ical/(?P<ical_token>[-\w\d]+).ics$', ICalFeedView.as_view(), name='ical-feed'),
    path('', RedirectView.as_view(url='v1/')),
]

if 'reports' in settings.INSTALLED_APPS:
    from reports.api import DailyReservationsReport, ReservationDetailsReport
    urlpatterns.extend([
        path('reports/daily_reservations/', DailyReservationsReport.as_view(), name='daily-reservations-report'),
        path('reports/reservation_details/', ReservationDetailsReport.as_view(), name='reservation-details-report'),
    ])


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
