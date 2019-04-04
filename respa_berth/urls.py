from respa_berth import admin
from django.conf.urls import include, url
from rest_framework.routers import DefaultRouter
from respa_berth.api.berth_reservation import PurchaseView, RenewalView, BerthReservationViewSet, SmsView
from respa_berth.api.berth import BerthViewSet, GroundBerthPriceView
from respa_berth.api.unit import UnitViewSet
from respa_berth.api.user import UserViewSet
from respa_berth.views.spa import IndexView
from respa_berth.api.importer import ImporterView

berth_router = DefaultRouter()
berth_router.register(r'berth_reservation', BerthReservationViewSet)
berth_router.register(r'berth', BerthViewSet)
berth_router.register(r'unit', UnitViewSet, 'berth-unit')
berth_router.register(r'user', UserViewSet, 'berth-user')

urlpatterns = [
    url(r'^purchase/', PurchaseView.as_view()),
    url(r'^sms/', SmsView.as_view()),
    url(r'^renewal/', RenewalView.as_view()),
    url(r'^ground_berth_price/', GroundBerthPriceView.as_view()),
    url(r'^importer/', ImporterView.as_view()),
    url(r'^', include(berth_router.urls))
]
