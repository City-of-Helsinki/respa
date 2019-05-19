import pytest
from django.urls import reverse
from django.test.utils import override_settings

from users.models import User

login_url = reverse('respa_admin:login')
tunnistamo_login_url = reverse('respa_admin:tunnistamo-login')


@pytest.mark.django_db
def test_tunnistamo_login_redirects_to_helsinki_login(client):
    response = client.get(tunnistamo_login_url)
    assert response.status_code == 302
    assert response.url == '/accounts/helsinki/login/'


@pytest.mark.django_db
def test_tunnistamo_login_preserves_next(client):
    response = client.get(tunnistamo_login_url + '?next=/foo/bar/')
    assert response.status_code == 302
    assert response.url.endswith('?next=%2Ffoo%2Fbar%2F')


@pytest.mark.django_db
def test_tunnistamo_login_when_already_logged_in_as_non_staff(client):
    User.objects.create_user(username='testuser', password='pasw123')
    initial_login_ok = client.login(username='testuser', password='pasw123')
    assert initial_login_ok
    response = client.get(tunnistamo_login_url)
    assert response.status_code == 302
    assert response.url == 'https://api.hel.fi/sso/logout/?next={url}'.format(
        url=('http://testserver/ra/login/tunnistamo/'
             .replace(':', '%3A').replace('/', '%2F')))


@pytest.mark.django_db
def test_login_view_render(client):
    response = client.get(login_url, HTTP_ACCEPT_LANGUAGE='en')
    assert response.status_code == 200
    assert isinstance(response.content, bytes)
    content = response.content.decode('utf-8')
    assert content.strip().startswith('<!DOCTYPE html>')
    assert '<title>Respa Admin - Log in</title>' in content
    assert 'href="/ra/login/tunnistamo/"' in content


@pytest.mark.django_db
@pytest.mark.parametrize('enabled', [True, False])
def test_login_view_render_username_login(client, enabled):
    with override_settings(RESPA_ADMIN_USERNAME_LOGIN=enabled):
        response = client.get(login_url, HTTP_ACCEPT_LANGUAGE='en')
        assert response.status_code == 200
        assert isinstance(response.content, bytes)
        content = response.content.decode('utf-8')
        if enabled:
            assert '<form method="post">' in content
            assert 'csrfmiddlewaretoken' in content
            assert '<input' in content
            assert 'name="username"' in content
            assert 'name="password"' in content
            assert '<button type="submit"' in content
        else:
            assert '<form' not in content
            assert 'name="username"' not in content


@pytest.mark.django_db
@pytest.mark.parametrize('enabled', [True, False])
@pytest.mark.parametrize('password', [
    'correct_password', 'wrong_password'])
def test_login_view_handle_username_login(client, enabled, password):
    User.objects.create_user(username='testuser', password='correct_password')
    with override_settings(RESPA_ADMIN_USERNAME_LOGIN=enabled):
        data = {'username': 'testuser', 'password': password}
        response = client.post(login_url, data=data, HTTP_ACCEPT_LANGUAGE='en')
        content = response.content.decode('utf-8')
        if enabled and password == 'correct_password':
            assert response.status_code == 302
            assert response.url == reverse('respa_admin:index')
            assert content == ''
        elif enabled:
            assert response.status_code == 200
            assert 'Login failed' in content
        else:
            assert response.status_code == 400
            assert content == 'Username login not allowed'


@pytest.mark.django_db
@pytest.mark.parametrize('user_kind', ['non-admin', 'admin'])
def test_login_view_already_logged_in(client, user_kind):
    user = User.objects.create_user(username='testuser', password='pasw123')
    if user_kind == 'admin':
        user.is_staff = True
        user.save()
    initial_login_ok = client.login(username='testuser', password='pasw123')
    assert initial_login_ok
    response = client.get(login_url, HTTP_ACCEPT_LANGUAGE='en')
    content = response.content.decode('utf-8')
    assert response.status_code == 200
    not_allowed_text = 'You are not allowed to use Respa Admin.'
    if user_kind == 'non-admin':
        assert not_allowed_text in content
    else:
        assert not_allowed_text not in content
    assert 'Log in' in content


@pytest.mark.django_db
def test_logout(client):
    user = User.objects.create_user(username='testuser', password='pasw123')
    initial_login_ok = client.login(username='testuser', password='pasw123')
    assert initial_login_ok
    assert client.session['_auth_user_id'] == str(user.id)
    response = client.get(reverse('respa_admin:logout'))
    assert response.status_code == 302
    assert response.url == (
        'https://api.hel.fi/sso/logout/?next=http%3A%2F%2Ftestserver%2Fra%2F')
    assert '_auth_user_id' not in client.session
