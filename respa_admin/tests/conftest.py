import pytest

from resources.tests.conftest import (
    equipment_category,
    equipment,
    general_admin,
    purpose,
    resource_in_unit,
    space_resource_type,
    terms_of_use,
    test_unit,
    test_unit2,
    general_admin,
    resource_in_unit,
    resource_in_unit2,
)


EMPTY_RESOURCE_FORM_DATA = {
    'images-TOTAL_FORMS': ['1'],
    'images-INITIAL_FORMS': ['0'],
    'images-MIN_NUM_FORMS': ['0'],
    'images-MAX_NUM_FORMS': ['1000'],

    'periods-TOTAL_FORMS': ['1'],
    'periods-INITIAL_FORMS': ['0'],
    'periods-MIN_NUM_FORMS': ['0'],
    'periods-MAX_NUM_FORMS': ['1000'],

    'unit': '',
    'type': '',
    'name': '',
    'description': '',
    'external_reservation_url': '',
    'purposes': '',
    'equipment': '',
    'responsible_contact_info': '',
    'people_capacity': '',
    'area': '',
    'min_period': '',
    'max_period': '',
    'reservable_max_days_in_advance': '',
    'max_reservations_per_user': '',
    'reservable': '',
    'reservation_info': '',
    'need_manual_confirmation': '',
    'authentication': '',
    'access_code_type': '',
    'max_price_per_hour': '',
    'min_price_per_hour': '',
    'generic_terms': '',
    'specific_terms': '',
    'reservation_confirmed_notification_extra': '',

    'images-0-caption': '',
    'images-0-type': '',
    'images-0-id': '',
    'images-0-resource': '',

    'periods-0-name': '',
    'periods-0-start': '',
    'periods-0-end': '',
    'periods-0-id': '',
    'periods-0-resource': '',

    'days-periods-0-TOTAL_FORMS': ['1'],
    'days-periods-0-INITIAL_FORMS': ['0'],
    'days-periods-0-MIN_NUM_FORMS': ['0'],
    'days-periods-0-MAX_NUM_FORMS': ['7'],

    'days-periods-0-0-weekday': '',
    'days-periods-0-0-opens': '',
    'days-periods-0-0-closes': '',
    'days-periods-0-0-closed': '',
    'days-periods-0-0-id': '',
    'days-periods-0-0-period': ''
}


@pytest.fixture
def empty_resource_form_data():
    return EMPTY_RESOURCE_FORM_DATA.copy()


@pytest.fixture
def valid_resource_form_data(
    equipment, terms_of_use, purpose, space_resource_type, test_unit, empty_resource_form_data
):
    data = empty_resource_form_data
    data.update({
        'access_code_type': 'pin6',
        'authentication': 'weak',
        'equipment': equipment.pk,
        'external_reservation_url': 'http://calendar.example.tld',
        'generic_terms': terms_of_use.pk,
        'max_period': '01:00:00',
        'min_period': '00:30:00',
        'name_fi': 'Test resource',
        'purposes': purpose.pk,
        'type': space_resource_type.pk,
        'unit': test_unit.pk,
        'periods-0-name': 'Kesäkausi',
        'periods-0-start': '2018-06-06',
        'periods-0-end': '2018-08-01',
        'days-periods-0-0-opens': '08:00',
        'days-periods-0-0-closes': '12:00',
        'days-periods-0-0-weekday': '1',
    })
    return data
