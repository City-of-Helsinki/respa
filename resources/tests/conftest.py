# -*- coding: utf-8 -*-
import pytest
import datetime
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APIClient, APIRequestFactory

from resources.enums import UnitAuthorizationLevel
from resources.models import Resource, ResourceType, Unit, UnitIdentifier, Purpose, Day, Period
from resources.models import Equipment, EquipmentAlias, ResourceEquipment, EquipmentCategory, TermsOfUse, ResourceGroup
from resources.models import AccessibilityValue, AccessibilityViewpoint, ResourceAccessibility, UnitAccessibility
from munigeo.models import Municipality


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def staff_api_client(staff_user):
    api_client = APIClient()
    api_client.force_authenticate(user=staff_user)
    return api_client


@pytest.fixture
def user_api_client(user):
    api_client = APIClient()
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture(params=[None, 'user', 'staff_user'])
def all_user_types_api_client(request):
    api_client = APIClient()
    if request.param:
        api_client.force_authenticate(request.getfixturevalue(request.param))
    return api_client


@pytest.fixture
def api_rf():
    return APIRequestFactory()


@pytest.mark.django_db
@pytest.fixture
def space_resource_type():
    return ResourceType.objects.get_or_create(id="test_space", name="test_space", main_type="space")[0]


@pytest.mark.django_db
@pytest.fixture
def space_resource(space_resource_type):
    return Resource.objects.create(type=space_resource_type, authentication="none", name="resource")


@pytest.mark.django_db
@pytest.fixture
def test_unit():
    return Unit.objects.create(name="unit", time_zone='Europe/Helsinki')


@pytest.mark.django_db
@pytest.fixture
def test_unit2():
    return Unit.objects.create(name="unit 2", time_zone='Europe/Helsinki')


@pytest.mark.django_db
@pytest.fixture
def test_unit3():
    unit = Unit.objects.create(name="unit 3", time_zone='Europe/Helsinki')
    UnitIdentifier.objects.create(unit=unit, namespace='internal', value=1)
    return unit


@pytest.mark.django_db
@pytest.fixture
def test_unit4():
    unit = Unit.objects.create(name="unit 4", time_zone='Europe/Helsinki')
    UnitIdentifier.objects.create(unit=unit, namespace='internal', value=1)
    return unit


@pytest.mark.django_db
@pytest.fixture
def generic_terms():
    return TermsOfUse.objects.create(
        name_fi='testikäyttöehdot',
        name_en='test terms of use',
        text_fi='kaikki on kielletty',
        text_en='everything is forbidden',
    )


@pytest.mark.django_db
@pytest.fixture
def payment_terms():
    return TermsOfUse.objects.create(
        name_fi='testimaksuehdot',
        name_en='test terms of payment',
        text_fi='kaikki on maksullista',
        text_en='everything is chargeable',
        terms_type=TermsOfUse.TERMS_TYPE_PAYMENT
    )


@pytest.mark.django_db
@pytest.fixture
def resource_in_unit(space_resource_type, test_unit, generic_terms, payment_terms):
    return Resource.objects.create(
        type=space_resource_type,
        authentication="none",
        name="resource in unit",
        unit=test_unit,
        max_reservations_per_user=1,
        max_period=datetime.timedelta(hours=2),
        reservable=True,
        generic_terms=generic_terms,
        payment_terms=payment_terms,
        specific_terms_fi='spesifiset käyttöehdot',
        specific_terms_en='specific terms of use',
        reservation_confirmed_notification_extra_en='this resource rocks'
    )


@pytest.mark.django_db
@pytest.fixture
def resource_in_unit2(space_resource_type, test_unit2):
    return Resource.objects.create(
        type=space_resource_type,
        authentication="none",
        name="resource in unit 2",
        unit=test_unit2,
        max_reservations_per_user=2,
        max_period=datetime.timedelta(hours=4),
        reservable=True,
    )


@pytest.mark.django_db
@pytest.fixture
def resource_in_unit3(space_resource_type, test_unit3):
    return Resource.objects.create(
        type=space_resource_type,
        authentication="none",
        name="resource in unit 3",
        unit=test_unit3,
        max_reservations_per_user=2,
        max_period=datetime.timedelta(hours=4),
        reservable=True,
    )


@pytest.mark.django_db
@pytest.fixture
def resource_in_unit4(space_resource_type, test_unit4):
    return Resource.objects.create(
        type=space_resource_type,
        authentication="none",
        name="resource in unit 4",
        unit=test_unit4,
        max_reservations_per_user=2,
        max_period=datetime.timedelta(hours=4),
        reservable=True,
    )


@pytest.mark.django_db
@pytest.fixture
def resource_with_opening_hours(resource_in_unit):
    p1 = Period.objects.create(start=datetime.date(2115, 1, 1),
                               end=datetime.date(2115, 12, 31),
                               resource=resource_in_unit, name='regular hours')
    for weekday in range(0, 7):
        Day.objects.create(period=p1, weekday=weekday,
                           opens=datetime.time(8, 0),
                           closes=datetime.time(18, 0))
    resource_in_unit.update_opening_hours()
    return resource_in_unit


@pytest.mark.django_db
@pytest.fixture
def exceptional_period(resource_with_opening_hours):
    parent = resource_with_opening_hours.periods.first()
    period = Period.objects.create(start='2115-01-10', end='2115-01-12',
                                   resource=resource_with_opening_hours,
                                   name='exceptional hours',
                                   exceptional=True, parent=parent)

    date = period.start
    Day.objects.create(period=period, weekday=date.weekday(),
                       closed=True)
    date = date + datetime.timedelta(days=1)
    Day.objects.create(period=period, weekday=date.weekday(),
                       opens='12:00', closes='13:00')
    date = date + datetime.timedelta(days=1)
    Day.objects.create(period=period, weekday=date.weekday(),
                       closed=True)

    return period


@pytest.mark.django_db
@pytest.fixture
def equipment_category():
    return EquipmentCategory.objects.create(
        name='test equipment category'
    )


@pytest.mark.django_db
@pytest.fixture
def equipment(equipment_category):
    equipment = Equipment.objects.create(name='test equipment', category=equipment_category)
    return equipment


@pytest.mark.django_db
@pytest.fixture
def equipment_alias(equipment):
    equipment_alias = EquipmentAlias.objects.create(name='test equipment alias', language='fi', equipment=equipment)
    return equipment_alias


@pytest.mark.django_db
@pytest.fixture
def resource_equipment(resource_in_unit, equipment):
    data = {'test_key': 'test_value'}
    resource_equipment = ResourceEquipment.objects.create(
        equipment=equipment,
        resource=resource_in_unit,
        data=data,
        description='test resource equipment',
    )
    return resource_equipment


@pytest.mark.django_db
@pytest.fixture
def user():
    return get_user_model().objects.create(
        username='test_user',
        first_name='Cem',
        last_name='Kaner',
        email='cem@kaner.com',
        preferred_language='en'
    )


@pytest.mark.django_db
@pytest.fixture
def user2():
    return get_user_model().objects.create(
        username='test_user2',
        first_name='Brendan',
        last_name='Neutra',
        email='brendan@neutra.com'
    )


@pytest.mark.django_db
@pytest.fixture
def staff_user():
    return get_user_model().objects.create(
        username='test_staff_user',
        first_name='John',
        last_name='Staff',
        email='john@staff.com',
        is_staff=True,
        preferred_language='en'
    )


@pytest.mark.django_db
@pytest.fixture
def unit_admin_user(resource_in_unit):
    user = get_user_model().objects.create(
        username='test_admin_user',
        first_name='Inspector',
        last_name='Lestrade',
        email='lestrade@scotlandyard.co.uk',
        is_staff=True,
        preferred_language='en'
    )
    user.unit_authorizations.create(subject=resource_in_unit.unit, level=UnitAuthorizationLevel.admin)
    return user


@pytest.mark.django_db
@pytest.fixture
def unit_manager_user(resource_in_unit):
    user = get_user_model().objects.create(
        username='test_manager_user',
        first_name='Inspector',
        last_name='Lestrade',
        email='lestrade@scotlandyard.co.uk',
        is_staff=True,
        preferred_language='en'
    )
    user.unit_authorizations.create(subject=resource_in_unit.unit, level=UnitAuthorizationLevel.manager)
    return user


@pytest.mark.django_db
@pytest.fixture
def unit_viewer_user(resource_in_unit):
    user = get_user_model().objects.create(
        username='test_viewer_user',
        first_name='Inspector',
        last_name='Watson',
        email='watson@scotlandyard.co.uk',
        is_staff=True,
        preferred_language='en'
    )
    user.unit_authorizations.create(subject=resource_in_unit.unit, level=UnitAuthorizationLevel.viewer)
    return user


@pytest.mark.django_db
@pytest.fixture
def general_admin():
    return get_user_model().objects.create(
        username='test_general_admin',
        first_name='Genie',
        last_name='Manager',
        email='genie.manager@example.com',
        is_staff=True,
        is_general_admin=True,
        preferred_language='en'
    )


@pytest.mark.django_db
@pytest.fixture
def group():
    return Group.objects.create(name='test group')


@pytest.mark.django_db
@pytest.fixture
def purpose():
    return Purpose.objects.create(name='test purpose', id='test-purpose')


@pytest.fixture
def resource_group(resource_in_unit):
    group = ResourceGroup.objects.create(
        identifier='test_group',
        name='Test resource group'
    )
    group.resources.set([resource_in_unit])
    return group


@pytest.fixture
def resource_group2(resource_in_unit2):
    group = ResourceGroup.objects.create(
        identifier='test_group_2',
        name='Test resource group 2'
    )
    group.resources.set([resource_in_unit2])
    return group

@pytest.fixture
def test_municipality():
    municipality = Municipality.objects.create(
        id='foo',
        name='Foo'
    )
    return municipality


@pytest.fixture
def accessibility_viewpoint_wheelchair():
    vp = {"id": "10", "name_en": "I am a wheelchair user", "order_text": 10}
    return AccessibilityViewpoint.objects.create(**vp)


@pytest.fixture
def accessibility_viewpoint_hearing():
    vp = {"id": "20", "name_en": "I am hearing impaired", "order_text": 20}
    return AccessibilityViewpoint.objects.create(**vp)


@pytest.fixture
def accessibility_value_green():
    return AccessibilityValue.objects.create(value='green', order=10)


@pytest.fixture
def accessibility_value_red():
    return AccessibilityValue.objects.create(value='red', order=-10)


@pytest.fixture
def resource_with_accessibility_data(resource_in_unit, accessibility_viewpoint_wheelchair,
                                     accessibility_viewpoint_hearing, accessibility_value_green,
                                     accessibility_value_red):
    """ Resource is wheelchair accessible, not hearing accessible, unit is accessible to both """
    ResourceAccessibility.objects.create(
        resource=resource_in_unit,
        viewpoint=accessibility_viewpoint_wheelchair,
        value=accessibility_value_green,
        shortage_count=0,
    )
    ResourceAccessibility.objects.create(
        resource=resource_in_unit,
        viewpoint=accessibility_viewpoint_hearing,
        value=accessibility_value_red,
        shortage_count=0,
    )
    UnitAccessibility.objects.create(
        unit=resource_in_unit.unit,
        viewpoint=accessibility_viewpoint_wheelchair,
        value=accessibility_value_green,
        shortage_count=0,
    )
    UnitAccessibility.objects.create(
        unit=resource_in_unit.unit,
        viewpoint=accessibility_viewpoint_hearing,
        value=accessibility_value_green,
        shortage_count=0,
    )
    return resource_in_unit


@pytest.fixture
def resource_with_accessibility_data2(resource_in_unit2, accessibility_viewpoint_wheelchair,
                                      accessibility_viewpoint_hearing, accessibility_value_green,
                                      accessibility_value_red):
    """ Resource is hearing accessible, not wheelchair accessible, unit is accessible to both """
    ResourceAccessibility.objects.create(
        resource=resource_in_unit2,
        viewpoint=accessibility_viewpoint_wheelchair,
        value=accessibility_value_red,
        shortage_count=0,
    )
    ResourceAccessibility.objects.create(
        resource=resource_in_unit2,
        viewpoint=accessibility_viewpoint_hearing,
        value=accessibility_value_green,
        shortage_count=0,
    )
    UnitAccessibility.objects.create(
        unit=resource_in_unit2.unit,
        viewpoint=accessibility_viewpoint_wheelchair,
        value=accessibility_value_green,
        shortage_count=0,
    )
    UnitAccessibility.objects.create(
        unit=resource_in_unit2.unit,
        viewpoint=accessibility_viewpoint_hearing,
        value=accessibility_value_green,
        shortage_count=0,
    )
    return resource_in_unit2


@pytest.fixture
def resource_with_accessibility_data3(resource_in_unit3, accessibility_viewpoint_wheelchair,
                                      accessibility_viewpoint_hearing, accessibility_value_green,
                                      accessibility_value_red):
    """ Resource is accessible, unit is not """
    ResourceAccessibility.objects.create(
        resource=resource_in_unit3,
        viewpoint=accessibility_viewpoint_wheelchair,
        value=accessibility_value_green,
        shortage_count=0,
    )
    ResourceAccessibility.objects.create(
        resource=resource_in_unit3,
        viewpoint=accessibility_viewpoint_hearing,
        value=accessibility_value_green,
        shortage_count=0,
    )
    UnitAccessibility.objects.create(
        unit=resource_in_unit3.unit,
        viewpoint=accessibility_viewpoint_wheelchair,
        value=accessibility_value_red,
        shortage_count=0,
    )
    UnitAccessibility.objects.create(
        unit=resource_in_unit3.unit,
        viewpoint=accessibility_viewpoint_hearing,
        value=accessibility_value_red,
        shortage_count=0,
    )
    return resource_in_unit3


@pytest.fixture
def resource_with_accessibility_data4(resource_in_unit4, accessibility_viewpoint_wheelchair,
                                      accessibility_viewpoint_hearing, accessibility_value_green):
    """ Resource is accessible, unit is accessible """
    ResourceAccessibility.objects.create(
        resource=resource_in_unit4,
        viewpoint=accessibility_viewpoint_wheelchair,
        value=accessibility_value_green,
        shortage_count=0,
    )
    ResourceAccessibility.objects.create(
        resource=resource_in_unit4,
        viewpoint=accessibility_viewpoint_hearing,
        value=accessibility_value_green,
        shortage_count=0,
    )
    UnitAccessibility.objects.create(
        unit=resource_in_unit4.unit,
        viewpoint=accessibility_viewpoint_wheelchair,
        value=accessibility_value_green,
        shortage_count=0,
    )
    UnitAccessibility.objects.create(
        unit=resource_in_unit4.unit,
        viewpoint=accessibility_viewpoint_hearing,
        value=accessibility_value_green,
        shortage_count=0,
    )
    return resource_in_unit4

