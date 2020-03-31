from django.utils.translation import ugettext_lazy as _
from ..enums import UnitAuthorizationLevel, UnitGroupAuthorizationLevel

# Always update permissions.rst documentation accordingly after modifying this file!

RESOURCE_PERMISSIONS = (
    ('can_approve_reservation', _('Can approve reservation')),
    ('can_make_reservations', _('Can make reservations')),
    ('can_modify_reservations', _('Can modify reservations')),
    ('can_ignore_opening_hours', _('Can make reservations outside opening hours')),
    ('can_view_reservation_access_code', _('Can view reservation access code')),
    ('can_view_reservation_extra_fields', _('Can view reservation extra fields')),
    ('can_view_reservation_user', _('Can view reservation user')),
    ('can_access_reservation_comments', _('Can access reservation comments')),
    ('can_comment_reservations', _('Can create comments for a reservation')),
    ('can_view_reservation_catering_orders', _('Can view reservation catering orders')),
    ('can_modify_reservation_catering_orders', _('Can modify reservation catering orders')),
    ('can_view_reservation_product_orders', _('Can view reservation product orders')),
    ('can_modify_paid_reservations', _('Can modify paid reservations')),
    ('can_bypass_payment', _('Can bypass payment for paid reservations')),
    ('can_create_staff_event', _('Can create a reservation that is a staff event')),
    ('can_create_special_type_reservation', _('Can create reservations of a non-normal type')),
    ('can_bypass_manual_confirmation', _('Can bypass manual confirmation requirement for resources')),
    ('can_create_reservations_for_other_users', _('Can create reservations for other registered users')),
    ('can_create_overlapping_reservations', _('Can create overlapping reservations')),
    ('can_ignore_max_reservations_per_user', _('Can ignore resources max reservations per user rule')),
    ('can_ignore_max_period', _('Can ignore resources max period rule')),
)

UNIT_ROLE_PERMISSIONS = {
    'can_approve_reservation': [],
    'can_make_reservations': [
        UnitGroupAuthorizationLevel.admin,
        UnitAuthorizationLevel.admin,
        UnitAuthorizationLevel.manager
    ],
    'can_modify_reservations': [
        UnitGroupAuthorizationLevel.admin,
        UnitAuthorizationLevel.admin,
        UnitAuthorizationLevel.manager,
        UnitAuthorizationLevel.viewer
    ],
    'can_ignore_opening_hours': [
        UnitGroupAuthorizationLevel.admin,
        UnitAuthorizationLevel.admin,
        UnitAuthorizationLevel.manager
    ],
    'can_view_reservation_access_code': [
        UnitGroupAuthorizationLevel.admin,
        UnitAuthorizationLevel.admin,
        UnitAuthorizationLevel.manager,
        UnitAuthorizationLevel.viewer
    ],
    'can_view_reservation_extra_fields': [
        UnitGroupAuthorizationLevel.admin,
        UnitAuthorizationLevel.admin,
        UnitAuthorizationLevel.manager,
        UnitAuthorizationLevel.viewer
    ],
    'can_view_reservation_user': [
        UnitGroupAuthorizationLevel.admin,
        UnitAuthorizationLevel.admin,
        UnitAuthorizationLevel.manager,
        UnitAuthorizationLevel.viewer
    ],
    'can_access_reservation_comments': [
        UnitGroupAuthorizationLevel.admin,
        UnitAuthorizationLevel.admin,
        UnitAuthorizationLevel.manager,
        UnitAuthorizationLevel.viewer
    ],
    'can_comment_reservations': [
        UnitGroupAuthorizationLevel.admin,
        UnitAuthorizationLevel.admin,
        UnitAuthorizationLevel.manager,
        UnitAuthorizationLevel.viewer
    ],
    'can_view_reservation_catering_orders': [
        UnitGroupAuthorizationLevel.admin,
        UnitAuthorizationLevel.admin,
        UnitAuthorizationLevel.manager
    ],
    'can_modify_reservation_catering_orders': [],
    'can_view_reservation_product_orders': [],
    'can_modify_paid_reservations': [],
    'can_bypass_payment': [
        UnitGroupAuthorizationLevel.admin,
        UnitAuthorizationLevel.admin,
        UnitAuthorizationLevel.manager
    ],
    'can_create_staff_event': [
        UnitGroupAuthorizationLevel.admin,
        UnitAuthorizationLevel.admin,
        UnitAuthorizationLevel.manager
    ],
    'can_create_special_type_reservation': [
        UnitGroupAuthorizationLevel.admin,
        UnitAuthorizationLevel.admin,
        UnitAuthorizationLevel.manager
    ],
    'can_bypass_manual_confirmation': [
        UnitGroupAuthorizationLevel.admin,
        UnitAuthorizationLevel.admin,
        UnitAuthorizationLevel.manager
    ],
    'can_create_reservations_for_other_users': [
        UnitGroupAuthorizationLevel.admin,
        UnitAuthorizationLevel.admin
    ],
    'can_create_overlapping_reservations': [
        UnitGroupAuthorizationLevel.admin,
        UnitAuthorizationLevel.admin,
        UnitAuthorizationLevel.manager
    ],
    'can_ignore_max_reservations_per_user': [
        UnitGroupAuthorizationLevel.admin,
        UnitAuthorizationLevel.admin,
        UnitAuthorizationLevel.manager
    ],
    'can_ignore_max_period': [
        UnitGroupAuthorizationLevel.admin,
        UnitAuthorizationLevel.admin,
        UnitAuthorizationLevel.manager
    ]
}

UNIT_PERMISSIONS = [
    ('unit:' + name, description)
    for (name, description) in RESOURCE_PERMISSIONS
]

RESOURCE_GROUP_PERMISSIONS = [
    ('group:' + name, description)
    for (name, description) in RESOURCE_PERMISSIONS
]
