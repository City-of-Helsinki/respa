from django.utils.translation import ugettext_lazy as _
from enumfields import Enum


class UnitGroupAuthorizationLevel(Enum):
    admin = 'admin'

    class Labels:
        admin = _("unit group administrator")


class UnitAuthorizationLevel(Enum):
    admin = 'admin'
    manager = 'manager'
    viewer = 'viewer'

    class Labels:
        admin = _("unit administrator")
        manager = _("unit manager")
        viewer = _("unit viewer")

