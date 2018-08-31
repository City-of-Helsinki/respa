from enumfields import Enum


class UnitGroupAuthorizationLevel(Enum):
    admin = 'admin'


class UnitAuthorizationLevel(Enum):
    admin = 'admin'
    manager = 'manager'
