
from respa.settings import *

ROOT_URLCONF = 'deploy.urls'

try:
    place = MIDDLEWARE.index('django.middleware.security.SecurityMiddleware')
except ValueError:
    place = 0

MIDDLEWARE.insert(place, 'whitenoise.middleware.WhiteNoiseMiddleware')

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# To get Sentry report for URLs
import environ
env = environ.Env(DEBUG_REQUEST=(bool, False))
DEBUG_REQUEST = env('DEBUG_REQUEST')
