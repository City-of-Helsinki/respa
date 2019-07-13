from .api import DailyReservationsReport, ReservationDetailsReport, ReservationListReport
from django.conf.urls import url


urlpatterns = [
    url(r'^daily_reservations/', DailyReservationsReport.as_view(), name='daily-reservations-report'),
    url(r'^reservation_details/', ReservationDetailsReport.as_view(), name='reservation-details-report'),
    url(r'^reservation_list/', ReservationListReport.as_view(), name='reservation-list-report'),
]
