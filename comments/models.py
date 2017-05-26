from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.db import models
from django.contrib.gis.db.models import Q
from django.utils.translation import ugettext_lazy as _
from guardian.shortcuts import get_objects_for_user
from caterings.models import CateringOrder
from resources.models import Reservation, Unit

COMMENTABLE_MODELS = {
    'reservation': Reservation,
}

if getattr(settings, 'RESPA_CATERINGS_ENABLED', False):
    COMMENTABLE_MODELS.update({
        'catering_order': CateringOrder,
    })


def get_commentable_content_types():
    return ContentType.objects.get_for_models(*COMMENTABLE_MODELS.values()).values()


class CommentQuerySet(models.QuerySet):
    def can_view(self, user):
        if not user.is_authenticated():
            return self.none()

        allowed_reservation_units = get_objects_for_user(
            user, 'resources.can_access_reservation_comments', klass=Unit
        )
        allowed_reservation_ids = Reservation.objects.filter(
            Q(resource__unit__in=allowed_reservation_units) | Q(user=user)
        ).values_list('id', flat=True)

        allowed_catering_order_units = get_objects_for_user(
            user, 'resources.can_view_reservation_catering_orders', klass=Unit
        )
        allowed_catering_order_ids = CateringOrder.objects.filter(
            Q(reservation__resource__unit__in=allowed_catering_order_units) | Q(reservation__user=user)
        ).values_list('id', flat=True)

        reservation_content_type = ContentType.objects.get_for_model(Reservation)
        catering_order_content_type = ContentType.objects.get_for_model(CateringOrder)

        return self.filter(
            Q(created_by=user) |
            (Q(content_type=reservation_content_type) & Q(object_id__in=allowed_reservation_ids)) |
            (Q(content_type=catering_order_content_type) & Q(object_id__in=allowed_catering_order_ids))
        )


class Comment(models.Model):
    created_at = models.DateTimeField(verbose_name=_('Time of creation'), auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('Created by'),
                                   null=True, blank=True, related_name='%(class)s_created')
    text = models.TextField(verbose_name=_('Text'))
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to=lambda: {'id__in': (ct.id for ct in get_commentable_content_types())}
    )
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    objects = CommentQuerySet.as_manager()

    class Meta:
        ordering = ('id',)
        verbose_name = _('Comment')
        verbose_name_plural = _('Comments')
        index_together = (('content_type', 'object_id'),)

    def __str__(self):
        author = self.created_by.get_display_name() if self.created_by else 'Unknown author'
        text = self.text if len(self.text) < 40 else self.text[:37] + '...'
        return '%s %s %s: %s' % (self.content_type.model, self.object_id, author, text)

    @staticmethod
    def can_user_comment_object(user, target_object):
        if not (user and user.is_authenticated()):
            return False

        target_model = target_object.__class__
        if target_model not in COMMENTABLE_MODELS.values():
            return False

        if target_model == Reservation:
            if user == target_object.user:
                return True
            if user.has_perm('resources.can_access_reservation_comments', target_object.resource.unit):
                return True
        elif target_model == CateringOrder:
            if user == target_object.reservation.user:
                return True
            if user.has_perm('resources.can_view_reservation_catering_orders', target_object.reservation.resource.unit):
                return True
        return False
