import pytest
from django.core.urlresolvers import reverse

from users.models import User

login_url = reverse('respa_admin:respa-admin-login')


@pytest.mark.django_db
def test_login_redirects_to_helsinki_login(client):
    response = client.get(login_url)
    assert response.status_code == 302
    assert response.url == '/accounts/helsinki/login/'


@pytest.mark.django_db
def test_login_preserves_next(client):
    response = client.get(login_url + '?next=/foo/bar/')
    assert response.status_code == 302
    assert response.url.endswith('?next=%2Ffoo%2Fbar%2F')


@pytest.mark.django_db
def test_login_when_already_logged_in_as_non_staff(client):
    User.objects.create_user(username='testuser', password='pasw123')
    initial_login_ok = client.login(username='testuser', password='pasw123')
    assert initial_login_ok
    response = client.get(login_url)
    assert response.status_code == 302
    assert response.url == (
        'https://api.hel.fi/sso/logout/'
        '?next=http%3A%2F%2Ftestserver%2Fra%2Flogin%2F')
