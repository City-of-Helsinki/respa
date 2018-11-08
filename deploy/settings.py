
from respa.settings import *

# Get whitenoise for serving static files
try:
    place = MIDDLEWARE.index('django.middleware.security.SecurityMiddleware')
except ValueError:
    place = 0

MIDDLEWARE.insert(place, 'whitenoise.middleware.WhiteNoiseMiddleware')

import environ

deploy_env = environ.Env(
    USE_X_FORWARDED_HOST = (bool, False),
    SECURE_PROXY = (bool, False),
    MEDIA_ROOT = (str, "/usr/src/app/www")
)

USE_X_FORWARDED_HOST = deploy_env('USE_X_FORWARDED_HOST')

if deploy_env('SECURE_PROXY'):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
