from django.conf import settings

PAYMENT_API_KEY = getattr(settings, 'PAYMENT_API_KEY', '')
PAYMENT_API_SECRET = getattr(settings, 'PAYMENT_API_SECRET', '')

PAYMENT_URL_API = 'https://payform.bambora.com/pbwapi'
PAYMENT_URL_API_AUTH = '{}/auth_payment'.format(PAYMENT_URL_API)
PAYMENT_URL_API_TOKEN = '{}/token/{{token}}'.format(PAYMENT_URL_API)

PAYMENT_URL_NOTIFY = 'http://127.0.0.1:8000/v1/order-notify/'
