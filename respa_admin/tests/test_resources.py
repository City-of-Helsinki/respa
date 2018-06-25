import pytest
from django.test import Client

create_new_resource_url = '/ra/resource/new/'
edit_resource_url = '/ra/resource/edit/'


@pytest.mark.django_db
def test_create_invalid_resource(get_unpopulated_data):
    client = Client()
    data = get_unpopulated_data
    response = client.post(create_new_resource_url, data=data)

    assert response.context['form'].errors != {}


@pytest.mark.django_db
def test_create_valid_resource(get_populated_data):
    client = Client()
    data = get_populated_data
    response = client.post(create_new_resource_url, data=data)

    assert response.context['form'].errors == {}


@pytest.mark.django_db
def test_edit_resource(get_populated_data, get_new_resource):
    client = Client()
    resource = get_new_resource
    data = get_populated_data

    data['name'] = 'New name'
    data['access_code_type'] = 'pin6'
    data['authentication'] = 'strong'

    response = client.post(create_new_resource_url, data=data, kwargs=resource.pk)

    assert response.context['form'].errors == {}
