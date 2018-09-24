from urllib.parse import urlencode

from django.conf import settings
from django.contrib import auth as django_auth
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.urls import reverse
from django.views.generic.base import TemplateView
from helusers.providers.helsinki.views import HelsinkiOAuth2Adapter

from ..auth import is_allowed_user


class LoginView(TemplateView):
    template_name = "respa_admin/login.html"

    def get_context_data(self, login_failed=False, **kwargs):
        request = self.request
        user = request.user

        context = super().get_context_data(**kwargs)

        if _is_authenticated(user) and not is_allowed_user(user):
            context['not_allowed_user'] = True
        if login_failed:
            context['login_failed'] = True
        context['tunnistamo_login_url'] = _get_url_with_next(
            request, 'respa_admin:tunnistamo-login')
        context['show_login_form'] = self._allow_username_login()

        return context

    def post(self, request, *args, **kwargs):
        if not self._allow_username_login():
            return HttpResponseBadRequest("Username login not allowed")

        post_data = self.request.POST

        user = django_auth.authenticate(
            self.request,
            username=post_data.get('username'),
            password=post_data.get('password'))

        if not user:
            context = self.get_context_data(login_failed=True)
            return self.render_to_response(context)

        django_auth.login(self.request, user)

        next_url = self.request.GET.get('next', reverse('respa_admin:index'))
        return HttpResponseRedirect(next_url)

    def _allow_username_login(self):
        return getattr(settings, 'RESPA_ADMIN_USERNAME_LOGIN', False)


def tunnistamo_login(request):
    if _is_authenticated(request.user):
        # If user is already logged in with unallowed account, then log
        # out first, to allow re-login with another account.
        if not is_allowed_user(request.user):
            return _logout_locally_and_in_tunnistamo(request)

    url = _get_url_with_next(request, 'helsinki_login')
    return HttpResponseRedirect(url)


def _is_authenticated(user):
    return bool(user and user.is_authenticated)


def _get_url_with_next(request, url_name):
    url = reverse(url_name)
    next_url = request.GET.get('next', None)
    next_part = ('?' + urlencode({'next': next_url})) if next_url else ''
    return url + next_part


def logout(request):
    index_uri = reverse('respa_admin:index')
    return _logout_locally_and_in_tunnistamo(request, redirect_uri=index_uri)


def _logout_locally_and_in_tunnistamo(request, redirect_uri=None):
    """
    Log out locally and in Tunnistamo.

    :type request: django.http.HttpRequest
    """
    # First logout locally
    django_auth.logout(request)

    # Then logout from Tunnistamo with a redirect which points
    # back to this view with a given next parameter
    tunnistamo_url = HelsinkiOAuth2Adapter.profile_url.replace('/user/', '')
    next_param = urlencode({
        'next': request.build_absolute_uri(redirect_uri)
    })
    return HttpResponseRedirect(tunnistamo_url + '/logout/?' + next_param)
