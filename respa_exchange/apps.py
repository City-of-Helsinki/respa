from django.apps.config import AppConfig
from django.db.models.signals import post_save, pre_delete


class RespaExchangeAppConfig(AppConfig):
    name = 'respa_exchange'
    verbose_name = 'Respa-Exchange'

    def ready(self):
        """
        Wire up the signals for uploading reservations.
        """
        from respa_exchange.signals import handle_reservation_delete, handle_reservation_save
        post_save.connect(
            handle_reservation_save,
            sender='resources.Reservation',
            dispatch_uid='respa-exchange-save'
        )
        pre_delete.connect(
            handle_reservation_delete,
            sender='resources.Reservation',
            dispatch_uid='respa-exchange-delete'
        )
