from .base import all_views
from users.api import all_views as users_views
from .resource import ResourceListViewSet, ResourceViewSet, PurposeViewSet
from .reservation import ReservationViewSet
#from .unit import UnitViewSet
from .search import TypeaheadViewSet
from .equipment import EquipmentViewSet
from hmlvaraus.api.berth import BerthViewSet
from hmlvaraus.api.unit import UnitViewSet
from hmlvaraus.api.user import UserViewSet
from hmlvaraus.api.hml_reservation import HMLReservationViewSet

from rest_framework import routers


class RespaAPIRouter(routers.DefaultRouter):
    def __init__(self):
        super(RespaAPIRouter, self).__init__()
        self.registered_api_views = set()
        self._register_all_views()
        self.register("search", TypeaheadViewSet, base_name="search")

    def _register_view(self, view):
        if view['class'] in self.registered_api_views:
            return
        self.registered_api_views.add(view['class'])
        self.register(view['name'], view['class'], base_name=view.get("base_name"))

    def _register_all_views(self):
        for view in all_views:
            self._register_view(view)
        for view in users_views:
            self._register_view(view)
