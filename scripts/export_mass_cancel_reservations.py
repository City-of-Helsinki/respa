import time

from django.utils import timezone
from munigeo.models import Municipality

from resources.models import Reservation, Resource, ReservationCancelReason, ReservationCancelReasonCategory
from resources.models.utils import generate_reservation_xlsx

municipality_helsinki = Municipality.objects.get(id='helsinki')

reservations = Reservation.objects.filter(
    state__in=[Reservation.CONFIRMED, Reservation.REQUESTED],
    begin__gte='2020-12-20 23:59:59.99+02',
    end__lte='2021-01-10 23:59:59.99+02',
    staff_event=False,
    resource__unit__municipality=municipality_helsinki,
    resource__public=True
)

def serialize_reservations(reservation):
    from resources.models import RESERVATION_EXTRA_FIELDS
    res_data = {
        'id': str(reservation.pk),
        'unit': str(reservation.resource.unit),
        'resource': str(reservation.resource),
        'begin': reservation.begin,
        'end': reservation.end,
        'user': str(reservation.user),
        'staff_event': reservation.staff_event,
        'created_at': reservation.created_at,
    }
    for field in RESERVATION_EXTRA_FIELDS:
        if hasattr(reservation, field):
            res_data[field] = getattr(reservation, field)
    return res_data


res_dict = map(serialize_reservations, reservations)
xlsx = generate_reservation_xlsx(res_dict)

f = open("cancelled_reservations.xlsx", "wb")
f.write(xlsx)
f.close()


print('Excel-file for to be cancelled reservations has bee written to cancelled_reservations.xlsx.')