
from respa.settings import *

ROOT_URLCONF = 'deploy.urls'

try:
    place = MIDDLEWARE.index('django.middleware.security.SecurityMiddleware')
except ValueError:
    place = 0

MIDDLEWARE.insert(place, 'whitenoise.middleware.WhiteNoiseMiddleware')

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
