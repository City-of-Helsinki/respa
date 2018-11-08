import pytest
from django.test import RequestFactory
from django.utils import translation
from django.urls import reverse

from resources.models import Resource
from ..forms import get_period_formset

from .conftest import (
    empty_resource_form_data,
    valid_resource_form_data,
)


NEW_RESOURCE_URL = reverse('respa_admin:new-resource')


@pytest.mark.django_db
def test_period_formset_with_minimal_valid_data(valid_resource_form_data):
    request = RequestFactory().post(NEW_RESOURCE_URL, data=valid_resource_form_data)
    period_formset_with_days = get_period_formset(request)
    assert period_formset_with_days.is_valid()


@pytest.mark.django_db
def test_period_formset_with_invalid_period_data(valid_resource_form_data):
    data = valid_resource_form_data
    data.pop('periods-0-start')
    with translation.override('fi'):
        request = RequestFactory().post(NEW_RESOURCE_URL, data=data)
        period_formset_with_days = get_period_formset(request)
    assert period_formset_with_days.is_valid() is False
    assert period_formset_with_days.errors == [{
        '__all__': ["Aseta 'resource' tai 'unit'"],
        'start': ['Tämä kenttä vaaditaan.'],
    }]


@pytest.mark.django_db
def test_period_formset_with_invalid_days_data(valid_resource_form_data):
    data = valid_resource_form_data
    data.pop('days-periods-0-0-weekday')
    with translation.override('fi'):
        request = RequestFactory().post(NEW_RESOURCE_URL, data=data)
        period_formset_with_days = get_period_formset(request)
    assert period_formset_with_days.is_valid() is False
    assert period_formset_with_days.errors == [
        {'__all__': ['Tarkista aukioloajat.']}
    ]
    assert period_formset_with_days.forms[0].days.errors == [
        {'weekday': ['Tämä kenttä vaaditaan.']}
    ]


@pytest.mark.django_db
def test_create_resource_with_invalid_data_returns_errors(admin_client, empty_resource_form_data):
    with translation.override('fi'):
        response = admin_client.post(NEW_RESOURCE_URL, data=empty_resource_form_data)
    assert response.context['form'].errors == {
        'access_code_type': ['Tämä kenttä vaaditaan.'],
        'authentication': ['Tämä kenttä vaaditaan.'],
        'equipment': ['Valitse oikea vaihtoehto.  ei ole vaihtoehtojen joukossa.'],
        'min_period': ['Tämä kenttä vaaditaan.'],
        'name_fi': ['Tämä kenttä vaaditaan.'],
        'purposes': ['Valitse oikea vaihtoehto.  ei ole vaihtoehtojen joukossa.'],
        'type': ['Tämä kenttä vaaditaan.'],
        'unit': ['Tämä kenttä vaaditaan.'],
    }
    assert response.context['period_formset_with_days'].errors == [
        {'__all__': ['Tarkista aukioloajat.']}
    ]


@pytest.mark.django_db
def test_resource_creation_with_valid_data(admin_client, valid_resource_form_data):
    assert Resource.objects.count() == 0  # No resources in the db
    response = admin_client.post(NEW_RESOURCE_URL, data=valid_resource_form_data, follow=True)
    assert response.status_code == 200
    assert response.context['form'].errors == {}
    assert Resource.objects.count() == 1  # One new resource in db
    new_resource = Resource.objects.first()
    assert new_resource.periods.count() == 1
    assert new_resource.periods.first().days.count() == 1
    assert new_resource.periods.first().days.first().weekday == 1


@pytest.mark.django_db
def test_editing_resource_via_form_view(admin_client, valid_resource_form_data):
    assert Resource.objects.all().exists() is False
    # Create a resource via the form view
    response = admin_client.post(NEW_RESOURCE_URL, data=valid_resource_form_data, follow=True)
    assert response.status_code == 200
    resource = Resource.objects.first()

    # Edit the resource
    valid_resource_form_data.update({
        'name_fi': 'Edited name',
    })
    response = admin_client.post(
        reverse('respa_admin:edit-resource', kwargs={'resource_id': resource.id}),
        data=valid_resource_form_data,
        follow=True
    )
    assert response.status_code == 200
    assert Resource.objects.count() == 1  # Still only 1 resource in db

    # Validate that the changes did happen
    edited_resource = Resource.objects.first()
    assert edited_resource.name_fi == 'Edited name'
    assert resource.name_fi != edited_resource.name
