from django.dispatch import receiver
from resources.signals import reservation_modified, reservation_cancelled


@receiver(reservation_modified)
def handle_reservation_change(sender, instance, user, **kwargs):
    catering_orders = instance.catering_orders.all()
    if not catering_orders:
        return

    for order in catering_orders:
        order.send_modified_notification()


@receiver(reservation_cancelled)
def handle_reservation_cancellation(sender, instance, user, **kwargs):
    catering_orders = instance.catering_orders.all()
    if not catering_orders:
        return

    for order in catering_orders:
        order.send_deleted_notification()
