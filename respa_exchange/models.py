from django.db import models
from django.utils import timezone
from django.utils.encoding import force_text, python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from resources.models import Reservation, Resource
from respa_exchange.ews.objs import ItemID


@python_2_unicode_compatible
class ExchangeResource(models.Model):
    resource = models.OneToOneField(
        verbose_name=_('resource'),
        to=Resource,
        on_delete=models.PROTECT
    )
    sync_to_respa = models.BooleanField(
        verbose_name=_('sync Exchange to Respa'),
        help_text=_('if disabled, events will not be synced from the Exchange calendar to Respa'),
        default=True,
        db_index=True
    )
    sync_from_respa = models.BooleanField(
        verbose_name=_('sync Respa to Exchange'),
        help_text=_('if disabled, new events will not be synced from Respa to the Exchange calendar; pre-existing events continue to be updated'),
        default=True,
        db_index=True
    )
    principal_email = models.EmailField(
        verbose_name=_('principal email'),
        unique=True,
        help_text=_('the email address for this resource in Exchange')
    )

    class Meta:
        verbose_name = _("Exchange resource")
        verbose_name_plural = _("Exchange resources")

    def __str__(self):
        return "%s (%s)" % (self.principal_email, self.resource)


class ExchangeReservationQuerySet(models.QuerySet):
    def for_item_id(self, item_id):
        """

        :type item_id: respa_exchange.ews.objs.ItemID
        :return:
        """
        return self.filter(item_id_hash=item_id.hash)


@python_2_unicode_compatible
class ExchangeReservation(models.Model):
    reservation = models.OneToOneField(
        Reservation,
        on_delete=models.DO_NOTHING,  # The signal will (hopefully) deal with this
        editable=False
    )
    item_id_hash = models.CharField(
        # The MD5 hash of the item ID; results in shorter (=faster) DB indexes
        max_length=32,
        db_index=True,
        editable=False
    )
    principal_email = models.EmailField(editable=False)  # Cached resource principal email
    _item_id = models.CharField(max_length=200, blank=True, editable=False, db_column='item_id')
    _change_key = models.CharField(max_length=100, blank=True, editable=False, db_column='change_key')

    created_at = models.DateTimeField(
        verbose_name=_('time of creation'),
        default=timezone.now,
        editable=False
    )
    modified_at = models.DateTimeField(
        verbose_name=_('time of modification'),
        default=timezone.now,
        editable=False
    )

    objects = ExchangeReservationQuerySet.as_manager()

    class Meta:
        verbose_name = _("Exchange reservation")
        verbose_name_plural = _("Exchange reservations")

    def __str__(self):
        return force_text(self.reservation)

    def save(self, *args, **kwargs):
        self.clean()
        return super(ExchangeReservation, self).save(*args, **kwargs)

    @property
    def item_id(self):
        return ItemID(id=self._item_id, change_key=self._change_key)

    @item_id.setter
    def item_id(self, value):
        assert isinstance(value, ItemID)
        self._item_id = value.id
        self._change_key = value.change_key
        self.item_id_hash = value.hash
