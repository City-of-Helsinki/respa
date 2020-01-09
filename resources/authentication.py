from django.utils.translation import ugettext as _
from rest_framework import exceptions

from helusers.jwt import JWTAuthentication


class RespaJWTAuthentication(JWTAuthentication):
    def authenticate_credentials(self, payload):
        user = super().authenticate_credentials(payload)

        if user and not user.is_active:
            msg = _('User account is disabled.')
            raise exceptions.AuthenticationFailed(msg)

        return user
