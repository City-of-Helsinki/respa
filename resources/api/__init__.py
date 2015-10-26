from .base import all_views
from .resource import ResourceListViewSet, ResourceViewSet, PurposeViewSet
from .reservation import ReservationViewSet
from .unit import UnitViewSet

from rest_framework import routers


class RespaAPIRouter(routers.DefaultRouter):
    def __init__(self):
        super(RespaAPIRouter, self).__init__()
        self.registered_api_views = set()
        self.register_views()

    def register_views(self):
        for view in all_views:
            kwargs = {}
            if view['class'] in self.registered_api_views:
                continue

            self.registered_api_views.add(view['class'])

            if 'base_name' in view:
                kwargs['base_name'] = view['base_name']
            self.register(view['name'], view['class'], **kwargs)
