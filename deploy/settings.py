
from respa.settings import *

# Get whitenoise for serving static files
try:
    place = MIDDLEWARE.index('django.middleware.security.SecurityMiddleware')
except ValueError:
    place = 0

MIDDLEWARE.insert(place, 'whitenoise.middleware.WhiteNoiseMiddleware')

ROOT_URLCONF = 'deploy.urls'
