import pytest

from resources.tests.conftest import (
    test_unit,
    space_resource_type,
    equipment,
    terms_of_use,
    purpose,
    equipment_category,
    resource_in_unit
)


def _get_data():
    return {
        'images-TOTAL_FORMS': ['1'],
        'images-INITIAL_FORMS': ['0'],
        'images-MIN_NUM_FORMS': ['0'],
        'images-MAX_NUM_FORMS': ['1000'],

        'periods-TOTAL_FORMS': ['1'],
        'periods-INITIAL_FORMS': ['0'],
        'periods-MIN_NUM_FORMS': ['0'],
        'periods-MAX_NUM_FORMS': ['1000'],

        'unit': [''],
        'type': [''],
        'name': [''],
        'description': [''],
        'purposes': [''],
        'equipment': [''],
        'responsible_contact_info': [''],
        'people_capacity': [''],
        'area': [''],
        'min_period': [''],
        'max_period': [''],
        'reservable_days_in_advance': [''],
        'max_reservations_per_user': [''],
        'reservable': [''],
        'reservation_info': [''],
        'need_manual_confirmation': [''],
        'authentication': [''],
        'access_code_type': [''],
        'max_price_per_hour': [''],
        'min_price_per_hour': [''],
        'generic_terms': [''],
        'specific_terms': [''],
        'reservation_confirmed_notification_extra': [''],

        'images-0-caption': [''],
        'images-0-type': [''],
        'images-0-id': [''],
        'images-0-resource': [''],

        'periods-0-name': [''],
        'periods-0-start': [''],
        'periods-0-end': [''],
        'periods-0-id': [''],
        'periods-0-resource': [''],

        'days-periods-0-TOTAL_FORMS': ['1'],
        'days-periods-0-INITIAL_FORMS': ['0'],
        'days-periods-0-MIN_NUM_FORMS': ['0'],
        'days-periods-0-MAX_NUM_FORMS': ['7'],

        'days-periods-0-0-weekday': [''],
        'days-periods-0-0-opens': [''],
        'days-periods-0-0-closes': [''],
        'days-periods-0-0-closed': [''],
        'days-periods-0-0-id': [''],
        'days-periods-0-0-period': ['']
    }


@pytest.fixture
def get_populated_data():
    data = _get_data()

    name = 'Test'
    access_code_type = 'pin6'
    authentication = 'weak'
    min_period = '00:30:00'
    max_period = '01:00:00'

    data['name'] = name
    data['access_code_type'] = access_code_type
    data['authentication'] = authentication
    data['min_period'] = min_period
    data['max_period'] = max_period

    data['unit'] = test_unit().pk
    data['type'] = space_resource_type().pk
    data['equipment'] = equipment(equipment_category()).pk
    data['generic_terms'] = terms_of_use().pk
    data['purposes'] = purpose().pk

    return data


@pytest.fixture
def get_unpopulated_data():
    return _get_data()


@pytest.fixture
def get_new_resource():
    return resource_in_unit(space_resource_type(), test_unit(), terms_of_use())
