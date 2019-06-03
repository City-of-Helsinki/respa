from .settings import *


RESPA_CATERINGS_ENABLED = True
RESPA_COMMENTS_ENABLED = True
RESPA_PAYMENTS_ENABLED = True

RESPA_RESOURCE_SERIALIZER_CLASS = 'payments.api.ResourceSerializer'
RESPA_RESOURCE_DETAILS_SERIALIZER_CLASS = 'payments.api.ResourceDetailsSerializer'
