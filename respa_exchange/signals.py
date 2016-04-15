from django.conf import settings


def handle_reservation_save(instance, **kwargs):
    if not getattr(settings, "RESPA_EXCHANGE_ENABLED", True):
        return
    from respa_exchange.models import ExchangeResource, ExchangeReservation
    from respa_exchange.uploader import create_on_remote, update_on_remote

    if getattr(instance, "_from_exchange", False):
        # If we're creating this instance _from_ Exchange (in the Downloader),
        # we don't want to push it back up!
        return

    exchange_reservation = ExchangeReservation.objects.filter(reservation=instance).first()
    if not exchange_reservation:  # First sync? How exciting!
        exchange_resource = ExchangeResource.objects.filter(
            sync_from_respa=True, resource=instance.resource
        ).select_related("exchange").first()

        if not exchange_resource:  # Not an Exchange-enabled resource; never mind.
            return

        exchange_reservation = ExchangeReservation(
            reservation=instance,
            exchange=exchange_resource.exchange,
            principal_email=exchange_resource.principal_email
        )

        create_on_remote(exchange_reservation)
    else:
        update_on_remote(exchange_reservation)


def handle_reservation_delete(instance, **kwargs):
    if not getattr(settings, "RESPA_EXCHANGE_ENABLED", True):
        return
    from respa_exchange.models import ExchangeReservation
    from respa_exchange.uploader import delete_on_remote

    exchange_reservation = ExchangeReservation.objects.filter(reservation=instance).first()
    if exchange_reservation:
        delete_on_remote(exchange_reservation)
        assert not exchange_reservation.pk
