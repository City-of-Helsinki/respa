from .base import all_views
from .resource import ResourceListViewSet, ResourceViewSet, PurposeViewSet
from .reservation import ReservationViewSet
from .unit import UnitViewSet
from .search import TypeaheadViewSet

from rest_framework import routers


class RespaAPIRouter(routers.DefaultRouter):
    def __init__(self):
        super(RespaAPIRouter, self).__init__()
        self.registered_api_views = set()
        self._register_views()
        self.register("search", TypeaheadViewSet, base_name="search")

    def _register_views(self):
        for view in all_views:
            if view['class'] in self.registered_api_views:
                continue
            self.registered_api_views.add(view['class'])
            self.register(view['name'], view['class'], base_name=view.get("base_name"))
