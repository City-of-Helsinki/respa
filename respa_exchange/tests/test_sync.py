from datetime import datetime, timedelta

import pytest
from django.utils.crypto import get_random_string
from resources.models.reservation import Reservation

from respa_exchange.ews.xml import NAMESPACES, M, T
from respa_exchange.models import ExchangeResource, ExchangeReservation
from respa_exchange.tests.session import SoapSeller


class CreateAndDeleteItemHandlers(object):
    def __init__(self, item_id, change_key):
        self.item_id = item_id
        self.change_key = change_key

    def handle_create(self, request):
        # Handle CreateItem responses; always return success
        if not request.xpath("//m:CreateItem", namespaces=NAMESPACES):
            return

        return M.CreateItemResponse(
            M.ResponseMessages(
                M.CreateItemResponseMessage(
                    {"ResponseClass": "Success"},
                    M.ResponseCode("NoError"),
                    M.Items(
                        T.CalendarItem(
                            T.ItemId(
                                Id=self.item_id,
                                ChangeKey=self.change_key
                            )
                        )
                    )
                )
            )
        )

    def handle_delete(self, request):
        # Handle DeleteItem responses; always return success
        if not request.xpath("//m:DeleteItem", namespaces=NAMESPACES):
            return
        return M.DeleteItemResponse(
            M.ResponseMessages(
                M.DeleteItemResponseMessage(
                    {"ResponseClass": "Success"},
                    M.ResponseCode("NoError"),
                )
            )
        )


@pytest.mark.django_db
@pytest.mark.parametrize("master_switch", (False, True))
@pytest.mark.parametrize("is_exchange_resource", (False, True))
@pytest.mark.parametrize("cancel_instead_of_delete", (False, True))
def test_create_and_delete_reservation(settings, master_switch, is_exchange_resource, space_resource, cancel_instead_of_delete):
    settings.RESPA_EXCHANGE_ENABLED = master_switch
    delegate = CreateAndDeleteItemHandlers(
        item_id=get_random_string(),
        change_key=get_random_string()
    )
    SoapSeller.wire(settings, delegate)
    if is_exchange_resource:
        ex_resource = ExchangeResource.objects.create(
            resource=space_resource,
            principal_email="test@example.com"
        )
    # Signals are called at creation time...
    res = Reservation.objects.create(
        resource=space_resource,
        begin=datetime.now(),
        end=datetime.now() + timedelta(minutes=30),
    )
    if master_switch and is_exchange_resource:
        # so now we should have a reservation in Exchange
        ex_resv = ExchangeReservation.objects.get(
            reservation=res
        )
        assert ex_resv.principal_email == ex_resource.principal_email
        assert ex_resv.item_id.id == delegate.item_id
        assert ex_resv.item_id.change_key == delegate.change_key
    else:
        assert not ExchangeReservation.objects.filter(reservation=res).exists()

    if cancel_instead_of_delete:  # But let's cancel it...
        res.set_state(Reservation.CANCELLED, user=None)
    else:  # But let's delete it...
        res.delete()

    # ... so our Exchange reservation gets destroyed.

    assert not ExchangeReservation.objects.filter(reservation=res).exists()
