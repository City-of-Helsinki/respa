from urllib.parse import urlencode

from django.contrib.auth import logout as auth_logout
from django.http import HttpResponseRedirect
from django.urls import reverse
from helusers.providers.helsinki.views import HelsinkiOAuth2Adapter

from ..auth import is_allowed_user


def login(request):
    if request.user and request.user.is_authenticated:
        # If user is already logged in with unallowed account, then log
        # out first, to allow re-login with another account.
        if not is_allowed_user(request.user):
            return _logout_locally_and_in_tunnistamo(request)

    next_url = request.GET.get('next', None)
    next_part = ('?' + urlencode({'next': next_url})) if next_url else ''
    url = reverse('helsinki_login') + next_part
    return HttpResponseRedirect(url)


def _logout_locally_and_in_tunnistamo(request):
    # First logout locally
    auth_logout(request)

    # Then logout from Tunnistamo with a redirect which points
    # back to this view with a given next parameter
    tunnistamo_url = HelsinkiOAuth2Adapter.profile_url.replace('/user/', '')
    next_param = urlencode({'next': request.build_absolute_uri()})
    return HttpResponseRedirect(tunnistamo_url + '/logout/?' + next_param)
