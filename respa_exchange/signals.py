from django.conf import settings

from respa_exchange.models import ExchangeReservation, ExchangeResource
from respa_exchange.uploader import create_on_remote, delete_on_remote, update_on_remote


def handle_reservation_save(instance, **kwargs):
    """
    Django signal handler for updating changed/created reservations on remote Exchanges.

    :param instance: A Reservation instance
    :type instance: resources.models.Reservation
    :param kwargs: The rest of the signal args
    :return:
    """
    if not getattr(settings, "RESPA_EXCHANGE_ENABLED", True):
        return

    if getattr(instance, "_from_exchange", False):
        # If we're creating this instance _from_ Exchange (in the Downloader),
        # we don't want to push it back up!
        return

    exchange_reservation = ExchangeReservation.objects.filter(
        reservation=instance,
        # If this reservation has come from Exchange,
        # we don't want to upload changes made to it.
        managed_in_exchange=False
    ).first()
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
    """
    Django signal handler for deleting reservation-related appointments from Exchange

    :param instance: A Reservation instance
    :type instance: resources.models.Reservation
    :param kwargs: The rest of the signal args
    :return:
    """
    if not getattr(settings, "RESPA_EXCHANGE_ENABLED", True):
        return

    exchange_reservation = ExchangeReservation.objects.filter(
        reservation=instance,
        # If this reservation has come from Exchange,
        # we don't want to upload deletions.
        managed_in_exchange=False
    ).first()
    if exchange_reservation:
        delete_on_remote(exchange_reservation)
        assert not exchange_reservation.pk
