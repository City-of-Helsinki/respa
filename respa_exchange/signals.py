from django.conf import settings


def handle_reservation_save(instance, **kwargs):
    if not getattr(settings, "RESPA_EXCHANGE_ENABLED", True):
        return
    from respa_exchange.models import ExchangeResource, ExchangeReservation
    exchange_reservation = ExchangeReservation.objects.filter(reservation=instance).first()
    if not exchange_reservation:  # First sync? How exciting!
        exchange_resource = ExchangeResource.objects.filter(sync_from_respa=True, resource=instance.resource).first()
        if not exchange_resource:  # Not an Exchange-enabled resource; never mind.
            return
        exchange_reservation = ExchangeReservation(
            reservation=instance,
            principal_email=exchange_resource.principal_email
        )

        exchange_reservation.create_on_remote()
    else:
        exchange_reservation.update_on_remote()


def handle_reservation_delete(instance, **kwargs):
    if not getattr(settings, "RESPA_EXCHANGE_ENABLED", True):
        return
    from respa_exchange.models import ExchangeReservation
    exchange_reservation = ExchangeReservation.objects.filter(reservation=instance).first()
    if exchange_reservation:
        exchange_reservation.delete_on_remote()
        assert not exchange_reservation.pk
