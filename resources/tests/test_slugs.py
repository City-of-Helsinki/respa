# -*- coding: utf-8 -*-
import pytest
from copy import deepcopy
from django.utils.translation import activate
from django.conf import settings
from django.apps import apps
from resources.models import Resource, Unit
from django.utils.module_loading import import_string

forwards = import_string("resources.migrations.0015_auto_20151028_1648.forwards")


@pytest.mark.django_db
@pytest.fixture
def unit():
    return Unit.objects.create(name="testiyksikko")


@pytest.mark.django_db
@pytest.fixture
def resource(space_resource_type, unit):
    return Resource.objects.create(
        type=space_resource_type,
        authentication="none",
        name="Testiyksikön testiresurssi",
        unit=unit
    )


@pytest.mark.django_db
def test_slug_created_alongside_object(unit, resource):
    """
    Test that a slug is generated when a Unit or a Resource is created.
    """
    assert unit.slug == "testiyksikko"
    assert resource.slug == "testiyksikon-testiresurssi"


@pytest.mark.django_db
@pytest.mark.skipif(len(settings.LANGUAGES) < 2,
                    reason="requires atleast two languages in LANGUAGES setting")
def test_slug_is_not_affected_by_current_language(space_resource_type):
    """
    Test that slugs are generated in the default language when
    it isn't the current activated language.
    """
    default_language = settings.LANGUAGES[0][0]
    other_language = settings.LANGUAGES[1][0]

    # change language before creating the objects
    activate(other_language)

    unit_name_kwargs = {
        "name_%s" % default_language: "Testiyksikkö",
        "name_%s" % other_language: "Test Unit"
    }
    unit = Unit.objects.create(**unit_name_kwargs)
    resource_name_kwargs = {
        "name_%s" % default_language: "Testiyksikön testiresurssi",
        "name_%s" % other_language: "Test unit's test resource"
    }
    resource = Resource.objects.create(
        unit=unit,
        type=space_resource_type,
        authentication="none",
        **resource_name_kwargs
    )
    assert unit.slug == "testiyksikko"
    assert resource.slug == "testiyksikon-testiresurssi"


@pytest.mark.django_db
def test_slug_generated_when_name_isnt_unique(unit, resource):
    """
    Test that slugs get generated correctly also when there are objects with
    the same name.
    """
    unit2 = deepcopy(unit)
    unit2.pk = None
    unit2.save()

    resource2 = deepcopy(resource)
    resource2.pk = None
    resource2.save()

    assert unit.slug == "testiyksikko"
    assert unit2.slug == "testiyksikko-2"

    assert resource.slug == "testiyksikon-testiresurssi"
    assert resource2.slug == "testiyksikon-testiresurssi-2"


@pytest.mark.django_db
def test_migration_slug_generator(unit, resource):
    """
    Test that the migration which adds slug fields also generates values for
    those.
    """

    # set initial fake values for slugs
    Unit.objects.filter(id=unit.id).update(slug="xxxfakeunit")
    Resource.objects.filter(id=resource.id).update(slug="xxxfakeresource")

    # execute the migration's slug generator
    forwards(apps, None, force=True)

    # check that the fake values are long gone
    unit.refresh_from_db()
    resource.refresh_from_db()
    assert unit.slug == "testiyksikko"
    assert resource.slug == "testiyksikon-testiresurssi"
