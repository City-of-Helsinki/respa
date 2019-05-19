from django.conf.urls import url
from django.contrib.auth.decorators import user_passes_test

from .permissions import can_login_to_respa_admin


def admin_url(pattern, view, name):
    """
    Define an URL pattern which requires Respa Admin login.
    """
    return url(pattern, admin_login_required(view), name=name)


def admin_login_required(function):
    """
    Decorator which requires login as Respa Admin allowed user.
    """
    decorator = user_passes_test(
        is_allowed_user,
        login_url='respa_admin:login')
    return decorator(function)


def is_allowed_user(user):
    """
    Test if given user is allowed to use Respa Admin.

    :type user: django.contrib.auth.models.AbstractUser
    :rtype: bool
    """
    if not user or not user.is_authenticated or not user.is_active:
        return False
    return can_login_to_respa_admin(user)
