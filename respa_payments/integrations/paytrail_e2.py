import re
import unicodedata
import urllib
from datetime import datetime
from hashlib import sha256
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError
from respa_payments.payments import PaymentIntegration
from respa_payments import settings, models


class PaytrailE2Integration(PaymentIntegration):
    def __init__(self, **kwargs):
        super(PaytrailE2Integration, self).__init__(**kwargs)
        self.service = 'VARAUS'
        self.merchant_id = settings.MERCHANT_ID
        self.merchant_auth_hash = settings.MERCHANT_AUTH_HASH
        self.payment_methods = '1,2,3,5,6,10,50,51,52,61'
        self.params_out = 'RETURN_AUTHCODE,PAYMENT_ID,AMOUNT,CURRENCY,PAYMENT_METHOD,TIMESTAMP,STATUS'
        self.params_in = (
            'MERCHANT_ID,'
            'URL_SUCCESS,'
            'URL_CANCEL,'
            'URL_NOTIFY,'
            'ORDER_NUMBER,'
            'PARAMS_IN,'
            'PARAMS_OUT,'
            'PAYMENT_METHODS,'
            'ITEM_TITLE[0],'
            'ITEM_ID[0],'
            'ITEM_QUANTITY[0],'
            'ITEM_UNIT_PRICE[0],'
            'ITEM_VAT_PERCENT[0],'
            'ITEM_DISCOUNT_PERCENT[0],'
            'ITEM_TYPE[0],'
            'PAYER_PERSON_PHONE,'
            'PAYER_PERSON_EMAIL,'
            'PAYER_PERSON_FIRSTNAME,'
            'PAYER_PERSON_LASTNAME,'
            'PAYER_PERSON_ADDR_STREET,'
            'PAYER_PERSON_ADDR_POSTAL_CODE,'
            'PAYER_PERSON_ADDR_TOWN')

    def unicode_to_paytrail(self, string):
        return unicodedata.normalize('NFD', string).encode('ascii', 'ignore')

    def construct_order_post(self, order_dict):
        super(PaytrailE2Integration, self).construct_order_post(order_dict)
        order = models.Order.objects.get(pk=order_dict.get('id'))
        resource_name = self.unicode_to_paytrail(order.sku.duration_slot.resource.name)
        data = {
            'MERCHANT_AUTH_HASH': self.merchant_auth_hash,
            'MERCHANT_ID': self.merchant_id,
            'URL_SUCCESS': self.url_success,
            'URL_CANCEL': self.url_cancel,
            'URL_NOTIFY': self.url_notify,
            'PARAMS_IN': self.params_in,
            'PARAMS_OUT': self.params_out,
            'PAYMENT_METHODS': self.payment_methods,
            'ORDER_NUMBER': self.service + '+' + resource_name + '+' + str(order_dict.get('id', '')),
            'ITEM_TITLE[0]': self.unicode_to_paytrail(order_dict.get('product', '')),
            'ITEM_ID[0]': order_dict.get('product_id', ''),
            'ITEM_QUANTITY[0]': 1,
            'ITEM_UNIT_PRICE[0]': order_dict.get('price', ''),
            'ITEM_VAT_PERCENT[0]': order_dict.get('vat', ''),
            'ITEM_DISCOUNT_PERCENT[0]': 0,
            'ITEM_TYPE[0]': 1,
            'PAYER_PERSON_PHONE': order_dict.get('reserver_phone_number', '').replace(' ', ''),
            'PAYER_PERSON_EMAIL': order_dict.get('reserver_email_address', ''),
            'PAYER_PERSON_FIRSTNAME': order_dict.get('reserver_name', ''),
            'PAYER_PERSON_LASTNAME': order_dict.get('reserver_name', ''),
            'PAYER_PERSON_ADDR_STREET': order_dict.get('billing_address_street', order_dict.get('reserver_address_street', '')),
            'PAYER_PERSON_ADDR_POSTAL_CODE': order_dict.get('billing_address_zip', order_dict.get('reserver_address_zip', '')),
            'PAYER_PERSON_ADDR_TOWN': order_dict.get('billing_address_city', order_dict.get('reserver_address_city', '')),
        }

        auth_code = data['MERCHANT_AUTH_HASH'] + '|' + \
            data['MERCHANT_ID'] + '|' + \
            data['URL_SUCCESS'] + '|' + \
            data['URL_CANCEL'] + '|' + \
            data['URL_NOTIFY'] + '|' + \
            str(data['ORDER_NUMBER']) + '|' + \
            data['PARAMS_IN'] + '|' + \
            data['PARAMS_OUT'] + '|' + \
            str(data['PAYMENT_METHODS']) + '|' + \
            data['ITEM_TITLE[0]'] + '|' + \
            str(data['ITEM_ID[0]']) + '|' + \
            str(data['ITEM_QUANTITY[0]']) + '|' + \
            str(data['ITEM_UNIT_PRICE[0]']) + '|' + \
            str(data['ITEM_VAT_PERCENT[0]']) + '|' + \
            str(data['ITEM_DISCOUNT_PERCENT[0]']) + '|' + \
            str(data['ITEM_TYPE[0]']) + '|' + \
            data['PAYER_PERSON_PHONE'] + '|' + \
            data['PAYER_PERSON_EMAIL'] + '|' + \
            data['PAYER_PERSON_FIRSTNAME'] + '|' + \
            data['PAYER_PERSON_LASTNAME'] + '|' + \
            data['PAYER_PERSON_ADDR_STREET'] + '|' + \
            data['PAYER_PERSON_ADDR_POSTAL_CODE'] + '|' + \
            data['PAYER_PERSON_ADDR_TOWN']

        auth_hash = sha256()
        auth_hash.update(auth_code.encode())
        data['AUTHCODE'] = auth_hash.hexdigest().upper()
        query_string = urllib.parse.urlencode(data, doseq=True)
        return {'redirect_url': self.api_url + '?' + query_string}

    def construct_payment_callback(self):
        callback = super(PaytrailE2Integration, self).construct_payment_callback()
        status = self.request.GET.get('STATUS', None)
        callback_data = {
            **callback,
            'redirect_url': self.url_redirect_callback or '',
            'payment_service_timestamp': datetime.fromtimestamp(int(self.request.GET.get('TIMESTAMP', None))),
            'payment_service_amount': self.request.GET.get('AMOUNT', None),
            'payment_service_currency': self.request.GET.get('CURRENCY', None),
            'payment_service_method': self.request.GET.get('PAYMENT_METHOD', None),
            'payment_service_return_authcode': self.request.GET.get('RETURN_AUTHCODE', None),
            'payment_service_status': status
        }
        if status == 'PAID':
            callback_data['payment_service_success'] = True
        return callback_data
