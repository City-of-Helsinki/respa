import pytest

from resources.models import Resource


@pytest.mark.django_db
def test_resource_creation(ac_resource):
    pass


@pytest.mark.django_db
def test_resource_with_access_code(test_driver, monkeypatch, ac_resource):
    """Test that Respa resource pre_save hook and AC resource hooks are working"""

    resource = ac_resource.resource
    resource.access_code_type = Resource.ACCESS_CODE_TYPE_PIN4
    resource.generate_access_codes = True
    resource.save()

    def save_resource(self, ac_resource):
        respa_resource = ac_resource.resource
        respa_resource.generate_access_codes = False
        respa_resource.save(update_fields=['generate_access_codes'])

    def save_respa_resource(self, ac_resource, respa_resource):
        respa_resource.generate_access_codes = False

    # First check that access control resource save hook is working
    with monkeypatch.context() as m:
        m.setattr(test_driver, 'save_resource', save_resource)
        ac_resource.save()
    resource.refresh_from_db()
    assert resource.generate_access_codes is False

    resource.generate_access_codes = True
    resource.save()

    # Then check that signal handlers are called when Respa resource
    # is saved
    with monkeypatch.context() as m:
        m.setattr(test_driver, 'save_respa_resource', save_respa_resource)
        resource.save()

    resource.refresh_from_db()
    assert resource.generate_access_codes is False
