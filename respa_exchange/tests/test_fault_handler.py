import pytest
from django.utils.encoding import force_text
from lxml.builder import E

from respa_exchange.downloader import sync_from_exchange
from respa_exchange.ews.session import SoapFault
from respa_exchange.ews.xml import S
from respa_exchange.models import ExchangeResource
from respa_exchange.tests.session import SoapSeller


class EverythingFails(object):
    code = 'nope'
    text = 'Das ist foreboden'

    def handle_everything(self, request):
        return S.Fault(
            E.faultcode(self.code),
            E.faultstring(self.text),
        )


@pytest.mark.django_db
def test_fault_handling(settings, space_resource, exchange):
    SoapSeller.wire(settings, EverythingFails())
    ex_resource = ExchangeResource.objects.create(
        resource=space_resource,
        principal_email="oh-bother@example.com",
        exchange=exchange,
        sync_to_respa=True,
    )
    with pytest.raises(SoapFault) as ei:
        sync_from_exchange(ex_resource)
    assert ei.type == SoapFault
    assert ei.value.code == EverythingFails.code
    assert ei.value.text == EverythingFails.text
    assert EverythingFails.code in force_text(ei.value)
    assert EverythingFails.text in force_text(ei.value)
