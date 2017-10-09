from datetime import timedelta

import pytest
from django.utils.crypto import get_random_string
from django.utils.timezone import now

from respa_exchange.downloader import sync_from_exchange
from respa_exchange.ews.objs import ItemID
from respa_exchange.models import ExchangeReservation, ExchangeResource
from respa_exchange.tests.handlers import FindItemsHandler
from respa_exchange.tests.session import SoapSeller
from respa_exchange.tests.utils import moments_close_enough


def _generate_item_dict():
    item_id = ItemID(get_random_string(), get_random_string())
    item_dict = {
        'id': item_id,
        'subject': get_random_string(),
        'start': now(),
        'end': now() + timedelta(hours=1),
        'organizer_name': 'Bob Dummy'
    }
    return item_dict


@pytest.mark.django_db
@pytest.mark.parametrize("sync_enabled", (False, True))
def test_download(
    settings, space_resource, exchange,
    sync_enabled
):
    email = "%s@example.com" % get_random_string()
    other_email = "%s@example.com" % get_random_string()
    item_dict = _generate_item_dict()
    other_item_dict = _generate_item_dict()
    item_id = item_dict["id"]
    delegate = FindItemsHandler()
    delegate.add_item(email, item_dict)
    delegate.add_item(email, other_item_dict)
    delegate.add_item(other_email, _generate_item_dict())  # We should never see this one

    SoapSeller.wire(settings, delegate)
    ex_resource = ExchangeResource.objects.create(
        resource=space_resource,
        principal_email=email,
        exchange=exchange,
        sync_to_respa=sync_enabled
    )
    assert ex_resource.reservations.count() == 0

    # First sync...
    sync_from_exchange(ex_resource)
    if not sync_enabled:
        assert ex_resource.reservations.count() == 0
        return  # No need to test the rest.
    assert ex_resource.reservations.count() == 2
    ex = _check_imported_reservation(item_id, item_dict)

    # Resync, with nothing changed:
    sync_from_exchange(ex_resource)
    assert ex_resource.reservations.count() == 2
    assert _check_imported_reservation(item_id, item_dict).modified_at == ex.modified_at  # No resave occurred

    # Simulate a change on the Exchange end
    item_dict["end"] += timedelta(hours=2)
    sync_from_exchange(ex_resource)
    assert ex_resource.reservations.count() == 2
    _check_imported_reservation(item_id, item_dict)

    # And simulate deleting one of our two items
    delegate.delete_item(email, item_id)
    sync_from_exchange(ex_resource)
    assert ex_resource.reservations.count() == 1


def _check_imported_reservation(item_id, item_dict):
    ex = ExchangeReservation.objects.filter(item_id_hash=item_id.hash).first()
    assert moments_close_enough(ex.reservation.begin, item_dict['start'])
    assert moments_close_enough(ex.reservation.end, item_dict['end'])

    return ex
