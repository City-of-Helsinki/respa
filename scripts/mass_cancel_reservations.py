import time

from django.utils import timezone
from munigeo.models import Municipality

from resources.models import Reservation, Resource, ReservationCancelReason, ReservationCancelReasonCategory
from resources.models.utils import generate_reservation_xlsx


municipality_helsinki = Municipality.objects.get(id='helsinki')

reservations = Reservation.objects.filter(
    state__in=[Reservation.CONFIRMED, Reservation.REQUESTED],
    begin__gte='2020-11-30 23:59:59.99+02',
    end__lte='2020-12-20 23:59:59.99+02',
    staff_event=False,
    resource__unit__municipality=municipality_helsinki,
    resource__public=True
)

cancel_reason_category = ReservationCancelReasonCategory.objects.get(name='Koronaperuutus')

for reservation in reservations:
    reservation.cancel_reason = ReservationCancelReason(
        reservation=reservation,
        category=cancel_reason_category,
        description='Koronaperuutus'
    )

    reservation.cancel_reason.save()
    reservation.set_state(Reservation.CANCELLED, None)

    print('Cancelled reservation {} for resource {}'.format(reservation.pk, reservation.resource.name))
    time.sleep(0.25)
