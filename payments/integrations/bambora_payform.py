import hmac
import hashlib
import logging
import requests
from urllib.parse import urlencode
from django.http import HttpResponseBadRequest

from .payments_base import PaymentsBase, PurchasedItem, Customer
from .. import settings
from ..models import Order

UI_RETURN_URL_PARAM_NAME = 'RESPA_UI_RETURN_URL'

logger = logging.getLogger()


class BamboraPayformPayments(PaymentsBase):
    """Bambora Payform specific integration utilities and configuration
    testing docs: https://payform.bambora.com/docs/web_payments/?page=testing
    api reference: https://payform.bambora.com/docs/web_payments/?page=full-api-reference
    """

    def __init__(self, **kwargs):
        super(BamboraPayformPayments, self).__init__(**kwargs)
        self.payment_methods_enabled = ['osuuspankki']
        self.url_payment_auth = settings.PAYMENT_URL_API_AUTH
        self.url_payment_token = settings.PAYMENT_URL_API_TOKEN

    def order_post(self, request, order_num, ui_return_url, purchased_items, customer):
        """Initiate payment by constructing the payload and posting it to Bambora"""
        respa_return_url = self.get_success_url(request)
        query_params = urlencode({UI_RETURN_URL_PARAM_NAME: ui_return_url})
        full_return_url = '{}?{}'.format(respa_return_url, query_params)

        payload = {
            'version': 'w3.1',
            'api_key': self.api_key,
            'payment_method': {
                'type': 'e-payment',
                'return_url': full_return_url,
                'notify_url': self.url_notify,
                'selected': self.payment_methods_enabled
            },
            'currency': 'EUR'
        }

        # TODO Info for the "bookkeeping ID" talpa requires
        # Tilino_Tulosyksikkö_Sisäinen tilaus_Projekti_Toimintoalue_ALV-koodi_Vapaaehtoinen oma tuotenumero
        payload['order_number'] = str(order_num)

        self.payload_add_products(payload, purchased_items)
        self.payload_add_customer(payload, customer)
        self.payload_add_auth_code(payload)

        r = requests.post(self.url_payment_auth, json=payload)
        if r.status_code == 200:
            json_response = r.json()
            result = json_response['result']
            if result == 0:
                return self.get_payment_url(json_response)
        # TODO Handle error cases
        # 1:  validation error
        # 2:  duplicate order number
        # 10: maintenance break

    def order_notify_callback(self):
        """Get response from bambora how the payment went

        Called asynchronously some time after user has completed payment,
        to mark payment process completed
        Sample params:
        ?AUTHCODE=769C463CFB93539F89EA58575AFD1B74E9D4C0DCA30AEF8981139B4DF6CAE8BE
        &RETURN_CODE=0
        &ORDER_NUMBER=test-order-131
        &SETTLED=1
        """
        result = self.request.GET.get('RETURN_CODE', '')
        print(result)

    def payload_add_products(self, payload, purchased_items):
        """Attach info of bought items to payload"""
        total_amount = 0
        items = []
        for item in purchased_items:
            total_amount += item.price
            items.append({
                'id': item.id,
                'title': item.title,
                'price': item.price,
                'pretax_price': item.pretax_price,
                'tax': item.tax,
                'count': item.count,
                'type': item.type
            })
        payload['amount'] = total_amount
        payload['products'] = items

    def payload_add_customer(self, payload, customer):
        """Attach customer data to payload"""
        payload.update({
            'email': customer.email,
            'customer': {
                'firstname': customer.firstname,
                'lastname': customer.lastname,
                'email': customer.email,
                'address_street': customer.address_street,
                'address_zip': customer.address_zip,
                'address_city': customer.address_city,
            }
        })

    def payload_add_auth_code(self, payload):
        """Construct auth code string and hash it into payload"""
        data = '{}|{}'.format(payload['api_key'], payload['order_number'])
        payload.update(authcode=self.calculate_auth_code(data))

    def get_customer(self, reservation):
        return Customer(firstname=reservation.reserver_name,
                        lastname=reservation.reserver_name,
                        email=reservation.reserver_email_address,
                        address_street=reservation.billing_address_street,
                        address_zip=reservation.billing_address_zip,
                        address_city=reservation.billing_address_city)

    def get_purchased_items(self, products_bought, reservation):
        for product in products_bought:
            yield PurchasedItem(
                id=product.code,
                title=product.name,
                price=int(product.get_price_for_reservation(reservation)) * 100,
                pretax_price=int(product.get_pretax_price_for_reservation(reservation)) * 100,
                tax=product.tax_percentage,
                count=1,
                type=1
            )

    def get_payment_url(self, json_response) -> str:
        """Where user should be directed to complete the payment
        Append "?minified" to get a stripped version
        """
        return self.url_payment_token.format(token=json_response['token'])

    def calculate_auth_code(self, data) -> str:
        return hmac.new(bytes(self.api_secret, 'latin-1'),
                        msg=bytes(data, 'latin-1'),
                        digestmod=hashlib.sha256).hexdigest().upper()

    def handle_success_request(self, request):
        logger.debug('Handling Bambora user return request, params: {}.'.format(request.GET))

        return_url = request.GET.get(UI_RETURN_URL_PARAM_NAME)
        if not return_url:
            # TODO should we actually make the whole thing fail here?
            logger.warning('Return URL missing.')
            return HttpResponseBadRequest()

        auth_code_calculation_values = [
            request.GET[param_name]
            for param_name in ('RETURN_CODE', 'ORDER_NUMBER', 'SETTLED', 'CONTACT_ID', 'INCIDENT_ID')
            if param_name in request.GET
        ]
        correct_auth_code = self.calculate_auth_code('|'.join(auth_code_calculation_values))
        auth_code = request.GET['AUTHCODE']
        if not hmac.compare_digest(auth_code, correct_auth_code):
            logger.warning('Incorrect auth code "{}".'.format(auth_code))
            return self.ui_redirect_failure(return_url)

        return_code = request.GET['RETURN_CODE']
        if return_code == '0':
            logger.debug('Payment completed successfully.')
            order = Order.objects.get(order_number=request.GET['ORDER_NUMBER'])
            order.status = Order.CONFIRMED
            order.save()
            return self.ui_redirect_success(return_url)
        elif return_code == '1':
            logger.debug('Payment failed.')
            order = Order.objects.get(order_number=request.GET['ORDER_NUMBER'])
            order.status = Order.REJECTED
            order.save()
            return self.ui_redirect_failure(return_url)
        elif return_code == '4':
            logger.debug('Transaction status could not be updated.')
            # TODO what should we do here? description of the situation:
            # Transaction status could not be updated after customer returned from the web page of a bank.
            # Please use the merchant UI to resolve the payment status.
            return self.ui_redirect_failure(return_url)
        elif return_code == '10':
            logger.debug('Maintenance break.')
            # TODO what now?
            return self.ui_redirect_failure(return_url)
        else:
            logger.debug('Incorrect RETURN_CODE "{}".'.format(return_code))
            return self.ui_redirect_failure(return_url)
