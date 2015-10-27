# -*- coding: utf-8 -*-
import json

import pytest
from django.utils.crypto import get_random_string
from django.utils.encoding import force_text

from resources.api.search import TypeaheadViewSet
from resources.models import Resource, Unit
from resources.tests.utils import assert_response_contains, assert_response_does_not_contain


@pytest.mark.django_db
@pytest.fixture
def typeahead_test_objects(space_resource_type):
    unit = Unit.objects.create(name="Testiyksikkö")
    sauna = Resource.objects.create(
        unit=unit, type=space_resource_type, authentication="none", name="Testiyksikön sauna"
    )
    meeting_room = Resource.objects.create(
        unit=unit, type=space_resource_type, authentication="none", name="Konferenssi"
    )
    return {"unit": unit, "sauna": sauna, "meeting_room": meeting_room}


@pytest.fixture(scope="module")
def typeahead_view():
    return TypeaheadViewSet.as_view({'get': 'list'})


@pytest.mark.django_db
def test_typeahead_api_bogus_type(rf, typeahead_view):
    # Test that bogus types are quietly skipped
    response = typeahead_view(request=rf.get("/", {"input": "testi", "types": "hello"}))
    assert_response_does_not_contain(response, '"id"')  # presence of an id means something was returned


@pytest.mark.django_db
def test_typeahead_api_bogus_query(rf, typeahead_view):
    # Test that bogus queries are skipped too
    response = typeahead_view(request=rf.get("/", {"input": "t k p"}))
    assert_response_does_not_contain(response, '"id"')  # presence of an id means something was returned


@pytest.mark.django_db
def test_typeahead_api_valid_query_with_no_results(rf, typeahead_view):
    # Test that bogus queries are skipped too
    response = typeahead_view(request=rf.get("/", {"input": get_random_string(32)}))
    assert_response_does_not_contain(response, '"id"')  # presence of an id means something was returned

@pytest.mark.django_db
def test_typeahead_api_unlimited(rf, typeahead_test_objects, typeahead_view):
    unit = typeahead_test_objects["unit"]
    sauna = typeahead_test_objects["sauna"]

    # Test unlimited requested objects; "testi" should get both the resource and the unit
    response = typeahead_view(request=rf.get("/", {"input": "testi"}))
    assert_response_contains(response, '"id":"%s"' % sauna.id)
    assert_response_contains(response, '"id":"%s"' % unit.id)


@pytest.mark.django_db
def test_typeahead_api_resource_only(rf, typeahead_test_objects, typeahead_view):
    unit = typeahead_test_objects["unit"]
    sauna = typeahead_test_objects["sauna"]

    # Test just the resource; the unit must not be there
    response = typeahead_view(request=rf.get("/", {"input": "testi", "types": "resource"}))
    assert_response_contains(response, '"id":"%s"' % sauna.id)
    assert_response_does_not_contain(response, '"id":"%s"' % unit.id)


@pytest.mark.django_db
def test_typeahead_api_unit_only(rf, typeahead_test_objects, typeahead_view):
    unit = typeahead_test_objects["unit"]
    sauna = typeahead_test_objects["sauna"]

    # Test just the unit; the resource must not be there
    response = typeahead_view(request=rf.get("/", {"input": "testi", "types": "unit"}))
    assert_response_does_not_contain(response, '"id":"%s"' % sauna.id)
    assert_response_contains(response, '"id":"%s"' % unit.id)


@pytest.mark.django_db
def test_typeahead_api_full_response(rf, typeahead_test_objects, typeahead_view):
    response = typeahead_view(request=rf.get("/", {"input": "testi", "full": "1"}))
    response.render()
    response_data = json.loads(force_text(response.content))
    # Check that we get more data than with the non-full mode for resources:
    assert all(key in response_data["resource"][0] for key in ("id", "type", "name", "unit"))
    assert all(key in response_data["unit"][0] for key in ("id", "time_zone", "name", "phone"))
