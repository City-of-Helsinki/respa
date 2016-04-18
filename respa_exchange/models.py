from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible
from django.utils.module_loading import import_string
from django.utils.translation import ugettext_lazy as _
from resources.models import Reservation, Resource

from respa_exchange.ews.objs import ItemID


@python_2_unicode_compatible
class ExchangeConfiguration(models.Model):
    """
    Encapsulates a configuration for a particular Exchange installation.
    """

    name = models.CharField(
        verbose_name=_('name'),
        unique=True,
        max_length=70,
        help_text=_('a descriptive name for this Exchange configuration')
    )
    url = models.URLField(
        verbose_name=_('EWS URL'),
        help_text=_('the URL to the Exchange Web Service (e.g. https://contoso.com/EWS/Exchange.asmx)')
    )
    username = models.CharField(
        verbose_name=_('username'),
        max_length=64,
        help_text=_('the service user to authenticate as, in domain\\username format')
    )
    password = models.CharField(
        verbose_name=_('password'),
        max_length=256,
        help_text=_('the user\'s password (stored as plain-text)'),
    )
    enabled = models.BooleanField(
        verbose_name=_('enabled'),
        default=True,
        db_index=True,
        help_text=_('whether synchronization is enabled at all against this Exchange instance')
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Exchange configuration")
        verbose_name_plural = _("Exchange configurations")

    def get_ews_session(self):
        """
        Get a configured EWS session.

        :rtype:   respa_exchange.ews.session.ExchangeSession
        """
        # TODO: Maybe cache or something? NTLM handshakes can take some time...
        session_class = import_string(
            getattr(settings, "RESPA_EXCHANGE_EWS_SESSION_CLASS", "respa_exchange.ews.session.ExchangeSession")
        )
        return session_class(
            url=self.url,
            username=self.username,
            password=self.password,
        )


@python_2_unicode_compatible
class ExchangeResource(models.Model):
    """
    Links a Respa resource to an Exchange calendar.
    """

    exchange = models.ForeignKey(
        verbose_name=_('Exchange configuration'),
        to=ExchangeConfiguration,
        on_delete=models.PROTECT,
        related_name='resources',
    )
    resource = models.OneToOneField(
        verbose_name=_('resource'),
        to=Resource,
        on_delete=models.PROTECT,
        related_name='exchange_resource',
    )
    sync_to_respa = models.BooleanField(
        verbose_name=_('sync Exchange to Respa'),
        help_text=_('if disabled, events will not be synced from the Exchange calendar to Respa'),
        default=True,
        db_index=True
    )
    sync_from_respa = models.BooleanField(
        verbose_name=_('sync Respa to Exchange'),
        help_text=_(
            'if disabled, new events will not be synced from Respa to the Exchange calendar; pre-existing events continue to be updated'),
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

    @property
    def reservations(self):
        """
        Get a queryset of ExchangeReservations for this resource

        :rtype: django.db.models.QuerySet[ExchangeReservation]
        """
        return ExchangeReservation.objects.filter(reservation__resource=self.resource)


@python_2_unicode_compatible
class ExchangeReservation(models.Model):
    """
    Links a Respa reservation with its Exchange item information.
    """

    reservation = models.OneToOneField(
        Reservation,
        on_delete=models.DO_NOTHING,  # The signal will (hopefully) deal with this
        editable=False,
        related_name='exchange_reservation',
    )
    item_id_hash = models.CharField(
        # The MD5 hash of the item ID; results in shorter (=faster) DB indexes
        max_length=32,
        db_index=True,
        editable=False
    )
    exchange = models.ForeignKey(  # Cached Exchange configuration
        to=ExchangeConfiguration,
        on_delete=models.PROTECT,
        editable=False,
        related_name='reservations',
    )
    managed_in_exchange = models.BooleanField(  # Whether or not this reservation came from Exchange
        db_index=True,
        editable=False,
        default=False
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

    class Meta:
        verbose_name = _("Exchange reservation")
        verbose_name_plural = _("Exchange reservations")

    def __str__(self):
        return "ExchangeReservation %s for %s (%s)" % (self.pk, self.reservation, self.principal_email)

    def save(self, *args, **kwargs):
        if not self.exchange_id:
            self.exchange = ExchangeResource.objects.get(resource=self.reservation.resource).exchange
        self.clean()
        return super(ExchangeReservation, self).save(*args, **kwargs)

    @property
    def item_id(self):
        """
        Retrieve the ExchangeReservation's related appointment's item ID object

        :rtype: respa_exchange.objs.ItemID
        """
        return ItemID(id=self._item_id, change_key=self._change_key)

    @item_id.setter
    def item_id(self, value):
        assert isinstance(value, ItemID)
        if self._item_id and self._item_id != value.id:
            raise ValueError("Can't mutate a reservation's item ID!")
        self._item_id = value.id
        self._change_key = value.change_key
        self.item_id_hash = value.hash
