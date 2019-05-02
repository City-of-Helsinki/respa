"""
Django settings for respa project.
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import environ
import raven
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ImproperlyConfigured


root = environ.Path(__file__) - 2  # two folders back
env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, ''),
    ALLOWED_HOSTS=(list, []),
    ADMINS=(list, []),
    DATABASE_URL=(str, 'postgis:///respa'),
    SECURE_PROXY_SSL_HEADER=(tuple, None),
    TOKEN_AUTH_ACCEPTED_AUDIENCE=(str, ''),
    TOKEN_AUTH_SHARED_SECRET=(str, ''),
    MEDIA_ROOT=(environ.Path(), root('media')),
    STATIC_ROOT=(environ.Path(), root('static')),
    MEDIA_URL=(str, '/media/'),
    STATIC_URL=(str, '/static/'),
    SENTRY_DSN=(str, ''),
    SENTRY_ENVIRONMENT=(str, ''),
    COOKIE_PREFIX=(str, 'respa'),
    INTERNAL_IPS=(list, []),
    MAIL_ENABLED=(bool, False),
    MAIL_DEFAULT_FROM=(str, ''),
    MAIL_MAILGUN_KEY=(str, ''),
    MAIL_MAILGUN_DOMAIN=(str, ''),
    MAIL_MAILGUN_API=(str, ''),
    RESPA_IMAGE_BASE_URL=(str, ''),
    ACCESSIBILITY_API_BASE_URL=(str, 'https://asiointi.hel.fi/kapaesteettomyys/'),
    ACCESSIBILITY_API_SYSTEM_ID=(str, ''),
    ACCESSIBILITY_API_SECRET=(str, ''),
    RESPA_ADMIN_INSTRUCTIONS_URL=(str, ''),
    RESPA_ADMIN_VIEW_RESOURCE_URL=(str, ''),
)
environ.Env.read_env()

# used for generating links to images, when no request context is available
# reservation confirmation emails use this
RESPA_IMAGE_BASE_URL = env('RESPA_IMAGE_BASE_URL')

BASE_DIR = root()

DEBUG_TOOLBAR_CONFIG = {
    'RESULTS_CACHE_SIZE': 100,
}
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env('ALLOWED_HOSTS')
ADMINS = env('ADMINS')
INTERNAL_IPS = env.list('INTERNAL_IPS',
                        default=(['127.0.0.1'] if DEBUG else []))
DATABASES = {
    'default': env.db()
}
DATABASES['default']['ATOMIC_REQUESTS'] = True

SECURE_PROXY_SSL_HEADER = env('SECURE_PROXY_SSL_HEADER')

SITE_ID = 1

# Application definition
INSTALLED_APPS = [
    'helusers',
    'modeltranslation',
    'parler',
    'grappelli',
    'django.forms',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'django.contrib.postgres',
    'rest_framework',
    'rest_framework_jwt',
    'rest_framework.authtoken',
    'django_filters',
    'corsheaders',
    'easy_thumbnails',
    'image_cropping',
    'guardian',
    'django_jinja',
    'anymail',
    'reversion',
    'django_admin_json_editor',

    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'helusers.providers.helsinki',

    'munigeo',

    'reports',
    'resources',
    'users',
    'caterings',
    'comments',
    'notifications.apps.NotificationsConfig',
    'kulkunen',

    'respa_exchange',
    'respa_admin',

    'sanitized_dump',
]

if env('SENTRY_DSN'):
    RAVEN_CONFIG = {
        'dsn': env('SENTRY_DSN'),
        'environment': env('SENTRY_ENVIRONMENT'),
        'release': raven.fetch_git_sha(BASE_DIR),
    }
    INSTALLED_APPS.append('raven.contrib.django.raven_compat')

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'respa.urls'
from django_jinja.builtins import DEFAULT_EXTENSIONS  # noqa

TEMPLATES = [
    {
        'BACKEND': 'django_jinja.backend.Jinja2',
        'APP_DIRS': True,
        'OPTIONS': {
            'extensions': DEFAULT_EXTENSIONS + ["jinja2.ext.i18n"],
            'translation_engine': 'django.utils.translation',
            "match_extension": ".jinja",
            "filters": {
                "django_wordwrap": "django.template.defaultfilters.wordwrap"
            },
        },
    },
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'respa.wsgi.application'

TEST_RUNNER = 'respa.test_runner.PyTestShimRunner'
TEST_PERFORMANCE = False

# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'fi'
LANGUAGES = (
    ('fi', _('Finnish')),
    ('en', _('English')),
    ('sv', _('Swedish'))
)

TIME_ZONE = 'Europe/Helsinki'

USE_I18N = True

USE_L10N = True

USE_TZ = True

LOCALE_PATHS = (
    os.path.join(BASE_DIR, 'locale'),
)

MODELTRANSLATION_FALLBACK_LANGUAGES = ('fi', 'en', 'sv')
MODELTRANSLATION_PREPOPULATE_LANGUAGE = 'fi'
PARLER_LANGUAGES = {
    SITE_ID: (
        {'code': 'fi'},
        {'code': 'en'},
        {'code': 'sv'},
    ),
}

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_URL = env('STATIC_URL')
MEDIA_URL = env('MEDIA_URL')
STATIC_ROOT = env('STATIC_ROOT')
MEDIA_ROOT = env('MEDIA_ROOT')

DEFAULT_SRID = 4326

CORS_ORIGIN_ALLOW_ALL = True

#
# Authentication
#
AUTH_USER_MODEL = 'users.User'
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
    'guardian.backends.ObjectPermissionBackend',
)

SOCIALACCOUNT_PROVIDERS = {
    'helsinki': {
        'VERIFIED_EMAIL': True
    }
}
LOGIN_REDIRECT_URL = '/'
ACCOUNT_LOGOUT_ON_GET = True
SOCIALACCOUNT_ADAPTER = 'helusers.adapter.SocialAccountAdapter'


# REST Framework
# http://www.django-rest-framework.org

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'helusers.jwt.JWTAuthentication',
    ] + ([
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ] if DEBUG else []),
    'DEFAULT_PAGINATION_CLASS': 'resources.pagination.DefaultPagination',
}

JWT_AUTH = {
    'JWT_PAYLOAD_GET_USER_ID_HANDLER': 'helusers.jwt.get_user_id_from_payload_handler',
    'JWT_AUDIENCE': env('TOKEN_AUTH_ACCEPTED_AUDIENCE'),
    'JWT_SECRET_KEY': env('TOKEN_AUTH_SHARED_SECRET')
}


CSRF_COOKIE_NAME = '%s-csrftoken' % env.str('COOKIE_PREFIX')
SESSION_COOKIE_NAME = '%s-sessionid' % env.str('COOKIE_PREFIX')


from easy_thumbnails.conf import Settings as thumbnail_settings  # noqa
THUMBNAIL_PROCESSORS = (
    'image_cropping.thumbnail_processors.crop_corners',
) + thumbnail_settings.THUMBNAIL_PROCESSORS


RESPA_MAILS_ENABLED = env('MAIL_ENABLED')
RESPA_MAILS_FROM_ADDRESS = env('MAIL_DEFAULT_FROM')
RESPA_CATERINGS_ENABLED = False
RESPA_COMMENTS_ENABLED = False
RESPA_DOCX_TEMPLATE = os.path.join(BASE_DIR, 'reports', 'data', 'default.docx')

RESPA_ADMIN_VIEW_RESOURCE_URL = env('RESPA_ADMIN_VIEW_RESOURCE_URL')

RESPA_ADMIN_ACCESSIBILITY_API_BASE_URL = env('ACCESSIBILITY_API_BASE_URL')
RESPA_ADMIN_ACCESSIBILITY_API_SYSTEM_ID = env('ACCESSIBILITY_API_SYSTEM_ID')
RESPA_ADMIN_ACCESSIBILITY_API_SECRET = env('ACCESSIBILITY_API_SECRET')
# list of ResourceType ids for which accessibility data input link is shown for
RESPA_ADMIN_ACCESSIBILITY_VISIBILITY = [
    'art_studio',  # Ateljee
    'avh553uaks6a',  # Soittohuone
    'band_practice_space',  # Bändikämppä
    'club_room',  # Kerhohuone
    'event_space',  # Tapahtumatila
    'game_space',  # Pelitila
    'hall',  # Sali
    'meeting_room',  # Kokoustila
    'multipurpose_room',  # Monitoimihuone"
    'studio',  # Studio
    'workspace',  # Työtila
]

RESPA_ADMIN_INSTRUCTIONS_URL = env('RESPA_ADMIN_INSTRUCTIONS_URL')

if env('MAIL_MAILGUN_KEY'):
    ANYMAIL = {
        'MAILGUN_API_KEY': env('MAIL_MAILGUN_KEY'),
        'MAILGUN_SENDER_DOMAIN': env('MAIL_MAILGUN_DOMAIN'),
        'MAILGUN_API_URL': env('MAIL_MAILGUN_API'),
    }
    EMAIL_BACKEND = 'anymail.backends.mailgun.EmailBackend'

RESPA_ADMIN_USERNAME_LOGIN = env.bool(
    'RESPA_ADMIN_USERNAME_LOGIN', default=True)

# local_settings.py can be used to override environment-specific settings
# like database and email that differ between development and production.
local_settings_path = os.path.join(BASE_DIR, "local_settings.py")
if os.path.exists(local_settings_path):
    with open(local_settings_path) as fp:
        code = compile(fp.read(), local_settings_path, 'exec')
    exec(code, globals(), locals())

# If a secret key was not supplied from elsewhere, generate a random one
# and store it into a file called .django_secret.
if 'SECRET_KEY' not in locals():
    secret_file = os.path.join(BASE_DIR, '.django_secret')
    try:
        with open(secret_file) as f:
            SECRET_KEY = f.read().strip()
    except IOError:
        import random
        system_random = random.SystemRandom()
        try:
            SECRET_KEY = ''.join([system_random.choice('abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)') for i in range(64)])
            secret = open(secret_file, 'w')
            os.chmod(secret_file, 0o0600)
            secret.write(SECRET_KEY)
            secret.close()
        except IOError:
            Exception('Please create a %s file with random characters to generate your secret key!' % secret_file)


#
# Validate config
#
if DATABASES['default']['ENGINE'] != 'django.contrib.gis.db.backends.postgis':
    raise ImproperlyConfigured("Only postgis database backend is supported")
