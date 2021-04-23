
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
env = environ.Env(
    DEBUG_REQUEST=(bool, False), 
    ELASTIC_APM_SERVER_URL=(str, ""))

DEBUG_REQUEST = env('DEBUG_REQUEST')

ELASTIC_APM_SERVER_URL = env('ELASTIC_APM_SERVER_URL')

if ELASTIC_APM_SERVER_URL:
    INSTALLED_APPS += [
    'elasticapm.contrib.django',
    ]
