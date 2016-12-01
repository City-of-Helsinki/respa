# -*- coding: utf-8 -*-
import pytest

from resources.api.base import TranslatedModelSerializer
from resources.models import ResourceEquipment


@pytest.mark.django_db
@pytest.fixture
def TMS():
    class TestSerializer(TranslatedModelSerializer):
        class Meta:
            model = ResourceEquipment
            fields = '__all__'
    return TestSerializer


@pytest.mark.django_db
def test_translated_model_serializer_language_filtering(TMS, equipment, space_resource):
    """
    Tests that TranslatedModelSerializer handles translated fields correctly
    when some or all of them are empty or None.

    ResourceEquipment model is used in the tests because it has description
    field that allows blank values.
    """
    tms = TMS()

    resource_equipment = ResourceEquipment.objects.create(
        equipment=equipment,
        resource=space_resource,
        description_fi='testiresurssissa olevan testivarusteen kuvaus',
        description_en=''
    )
    representation = tms.to_representation(resource_equipment)
    description = representation['description']
    assert description['fi'] == 'testiresurssissa olevan testivarusteen kuvaus'
    assert 'en' not in description  # empty field should not be included
    assert 'sv' not in description  # null field should not be included

    resource_equipment_descriptions_null = ResourceEquipment.objects.create(
        equipment=equipment,
        resource=space_resource,
    )
    representation = tms.to_representation(resource_equipment_descriptions_null)
    assert representation['description'] is None  # should be None as all description fields are null

    resource_equipment_descriptions_empty = ResourceEquipment.objects.create(
        equipment=equipment,
        resource=space_resource,
        description_fi='',
        description_en='',
        description_sv='',
    )

    representation = tms.to_representation(resource_equipment_descriptions_empty)
    assert representation['description'] is None  # should be None as all description fields are empty
