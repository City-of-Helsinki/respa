import re
import urllib
from hashlib import sha256
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError
from respa_payments.payments import PaymentIntegration
from respa_payments import settings


class PaytrailE2Integration(PaymentIntegration):
    def __init__(self, **kwargs):
        super(PaytrailE2Integration, self).__init__(**kwargs)
        self.merchant_id = settings.MERCHANT_ID
        self.merchant_auth_hash = settings.MERCHANT_AUTH_HASH
        self.payment_methods = '1,2,3,5,6,10,50,51,52,61'
        self.params_out = 'PAYMENT_ID,TIMESTAMP,STATUS'
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

    def construct_order_post(self, order):
        super(PaytrailE2Integration, self).construct_order_post(order)
        data = {
            'MERCHANT_AUTH_HASH': self.merchant_auth_hash,
            'MERCHANT_ID': self.merchant_id,
            'URL_SUCCESS': self.url_success,
            'URL_CANCEL': self.url_cancel,
            'URL_NOTIFY': self.url_notify,
            'PARAMS_IN': self.params_in,
            'PARAMS_OUT': self.params_out,
            'PAYMENT_METHODS': self.payment_methods,
            'ORDER_NUMBER': order.get('payment_service_order_number', None),
            'ITEM_TITLE[0]': order.get('product', None),
            'ITEM_ID[0]': order.get('id', None),
            'ITEM_QUANTITY[0]': 1,
            'ITEM_UNIT_PRICE[0]': order.get('price', None),
            'ITEM_VAT_PERCENT[0]': order.get('vat', None),
            'ITEM_DISCOUNT_PERCENT[0]': 0,
            'ITEM_TYPE[0]': 1,
            'PAYER_PERSON_PHONE': order.get('reserver_phone_number', None),
            'PAYER_PERSON_EMAIL': order.get('reserver_email_address', None),
            'PAYER_PERSON_FIRSTNAME': order.get('reserver_name', None),
            'PAYER_PERSON_LASTNAME': order.get('reserver_name', None),
            'PAYER_PERSON_ADDR_STREET': order.get('reserver_address_street', None),
            'PAYER_PERSON_ADDR_POSTAL_CODE': order.get('reserver_address_zip', None),
            'PAYER_PERSON_ADDR_TOWN': order.get('reserver_address_city', None),
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
        callback_data = {
            **callback,
            'redirect_url': self.url_redirect_callback or '',
            'payment_service_order_number': self.request.GET.get('ORDER_NUMBER', None),
            'payment_service_timestamp': self.request.GET.get('TIMESTAMP', None),
            'payment_service_paid': self.request.GET.get('PAID', None),
            'payment_service_method': self.request.GET.get('METHOD', None),
            'payment_service_return_authcode': self.request.GET.get('RETURN_AUTHCODE', None),
        }
        return callback_data

    def is_valid(self):
        is_valid = super(PaytrailE2Integration, self).is_valid()
        try:
            # Validate success callback
            str_to_check = '%(PAYMENT_ID)s|%(TIMESTAMP)s|%(STATUS)s' % self.request.GET
            str_to_check += '|%s' % self.merchant_auth_hash
            checksum = sha256(str_to_check.encode('utf-8')).hexdigest().upper()
            return checksum == self.request.GET.get('RETURN_AUTHCODE')
        except KeyError:
            try:
                # Validate failure callback
                str_to_check = '%(PAYMENT_ID)s|%(TIMESTAMP)s|%(STATUS)s' % self.request.GET
                str_to_check += '|%s' % self.merchant_auth_hash
                checksum = sha256(str_to_check.encode('utf-8')).hexdigest().upper()
                return checksum == self.request.GET.get('RETURN_AUTHCODE')
            except KeyError as e:
                raise ValidationError(_(e))
        return is_valid
