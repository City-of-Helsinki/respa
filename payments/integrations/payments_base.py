from collections import namedtuple
from payments import settings

PurchasedItem = namedtuple('PurchasedItem',
                           'id, title, price, pretax_price, tax count type')

Customer = namedtuple('Customer',
                      'firstname lastname email address_street address_zip address_city')


class PaymentsBase(object):
    """Common base for payment provider integrations"""

    def __init__(self, **kwargs):
        self.api_key = settings.PAYMENT_API_KEY
        self.api_secret = settings.PAYMENT_API_SECRET
        self.url_api = settings.PAYMENT_URL_API
        self.url_notify = settings.PAYMENT_URL_NOTIFY

    def order_post(self):
        raise NotImplementedError

    def order_notify_callback(self):
        raise NotImplementedError

    def get_customer(self):
        raise NotImplementedError

    def get_purchased_items(self):
        return []

    def calculate_auth_code(self, data):
        """Calculate and return a hash of some data

        As the hashing algorithms and data varies between providers
        there needs to be a subclass implementation"""
        raise NotImplementedError
