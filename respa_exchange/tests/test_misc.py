from datetime import timedelta

import pytest
from django.utils.timezone import now

from resources.models import Reservation
from respa_exchange.ews.objs import ItemID
from respa_exchange.models import ExchangeReservation, ExchangeResource


@pytest.mark.django_db
def test_exres_itemid_immutable(
    settings, space_resource, exchange
):
    settings.RESPA_EXCHANGE_ENABLED = False  # We'll do the work manually

    ExchangeResource.objects.create(
        resource=space_resource,
        principal_email="test@example.com",
        exchange=exchange
    )
    exres = ExchangeReservation(
        reservation=Reservation.objects.create(
            resource=space_resource,
            begin=now(),
            end=now() + timedelta(minutes=30),
        ),
    )
    exres.item_id = ItemID("bar", "foo")
    exres.save()

    with pytest.raises(ValueError):
        exres.item_id = ItemID("foo", "foo")
