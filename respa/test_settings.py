from .settings import *


RESPA_CATERINGS_ENABLED = True
RESPA_COMMENTS_ENABLED = True
RESPA_PAYMENTS_ENABLED = True
# Bambora Payform provider settings
RESPA_PAYMENTS_PROVIDER_CLASS = 'payments.providers.BamboraPayformProvider'
RESPA_PAYMENTS_BAMBORA_API_URL = 'https://real-bambora-api-url/api'
RESPA_PAYMENTS_BAMBORA_API_KEY = 'dummy-key'
RESPA_PAYMENTS_BAMBORA_API_SECRET = 'dummy-secret'
RESPA_PAYMENTS_BAMBORA_PAYMENT_METHODS = ['dummy-bank']
