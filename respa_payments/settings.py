from django.conf import settings

# Paytrail
MERCHANT_ID = getattr(settings, 'PAYTRAIL_MERCHANT_ID', '')
MERCHANT_AUTH_HASH = getattr(settings, 'PAYTRAIL_MERCHANT_AUTH_HASH', '')

# Payments
INTEGRATION_CLASS = getattr(settings, 'RESPA_PAYMENTS_INTEGRATION_CLASS', '')
PAYMENT_API_URL = getattr(settings, 'RESPA_PAYMENTS_API_URL', '')
URL_SUCCESS = getattr(settings, 'RESPA_PAYMENTS_URL_SUCCESS', '')
URL_NOTIFY = getattr(settings, 'RESPA_PAYMENTS_URL_NOTIFY', '')
URL_CANCEL = getattr(settings, 'RESPA_PAYMENTS_URL_CANCEL', '')
URL_REDIRECT_CALLBACK = getattr(settings, 'RESPA_PAYMENTS_URL_REDIRECT_CALLBACK', '')
