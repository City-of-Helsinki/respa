from django.utils.translation import ugettext as _
from rest_framework import exceptions
from rest_framework_jwt.settings import api_settings

from helusers.jwt import JWTAuthentication

jwt_get_username_from_payload = api_settings.JWT_PAYLOAD_GET_USERNAME_HANDLER


class RespaJWTAuthentication(JWTAuthentication):
    def authenticate_credentials(self, payload):
        user = super().authenticate_credentials(payload)

        if user and not user.is_active:
            msg = _('User account is disabled.')
            raise exceptions.AuthenticationFailed(msg)

        return user