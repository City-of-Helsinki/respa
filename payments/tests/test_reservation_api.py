import pytest
from rest_framework.reverse import reverse

from resources.models import Reservation
from resources.tests.conftest import resource_in_unit, user_api_client  # noqa
from resources.tests.test_reservation_api import day_and_period  # noqa

from ..factories import ProductFactory
from ..models import Product

LIST_URL = reverse('reservation-list')


@pytest.mark.parametrize('has_rent_product, expected_state', (
    (False, Reservation.CONFIRMED),
    (True, Reservation.WAITING_FOR_PAYMENT),
))
@pytest.mark.django_db
def test_reservation_creation_state(user_api_client, resource_in_unit, has_rent_product, expected_state):
    if has_rent_product:
        ProductFactory(type=Product.RENT, resources=[resource_in_unit])
    data = {
        'resource': resource_in_unit.pk,
        'begin': '2115-04-04T11:00:00+02:00',
        'end': '2115-04-04T12:00:00+02:00'
    }

    response = user_api_client.post(LIST_URL, data)
    assert response.status_code == 201, response.data
    new_reservation = Reservation.objects.last()
    assert new_reservation.state == expected_state
