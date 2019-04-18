import pytest
from django.test.utils import override_settings
from django.urls import reverse

from ..views.resources import SaveResourceView


@pytest.mark.django_db
@override_settings(RESPA_ADMIN_ACCESSIBILITY_API_BASE_URL='http://api.com/')
@override_settings(RESPA_ADMIN_ACCESSIBILITY_VISIBILITY=['test_space'])
@override_settings(RESPA_ADMIN_ACCESSIBILITY_API_SECRET='foo')
@override_settings(RESPA_ADMIN_ACCESSIBILITY_API_SYSTEM_ID='bar')
def test_accessibility_api_link_creation(rf, resource_in_unit, general_admin):
    url = reverse('respa_admin:edit-resource', kwargs={'resource_id': resource_in_unit.pk})
    request = rf.get(url)
    request.user = general_admin
    response = SaveResourceView.as_view()(request, resource_id=resource_in_unit.pk)
    accessibility_data_link = response.context_data.get('accessibility_data_link')
    assert accessibility_data_link is not None
    assert accessibility_data_link.startswith('http://api.com/')
