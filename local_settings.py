from respa.settings import *

DEBUG = True

SECRET_KEY = '!'

ALLOWED_HOSTS = ['*']

NOSE_ARGS = ['--nocapture',
             '--nologcapture',]

AUTH_PASSWORD_VALIDATORS = []

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        # 'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'respa',
        'USER': 'respa',
        'PASSWORD': 'respa',
        'HOST': 'localhost',
        'PORT': '5433',
    }
}

DATABASE_URL = 'postgis:///respa'

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'