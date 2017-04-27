from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.db import models
from django.utils.translation import ugettext_lazy as _

COMMENTABLE_MODELS = ('reservation',)


class Comment(models.Model):
    created_at = models.DateTimeField(verbose_name=_('Time of creation'), auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('Created by'),
                                   null=True, blank=True, related_name='%(class)s_created')
    text = models.TextField(verbose_name=_('Text'))
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to={'model__in': COMMENTABLE_MODELS}
    )
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        ordering = ('id',)
        verbose_name = _('Comment')
        verbose_name_plural = _('Comments')
        index_together = (('content_type', 'object_id'),)

    def __str__(self):
        author = self.created_by.get_display_name() if self.created_by else 'Unknown author'
        text = self.text if len(self.text) < 40 else self.text[:37] + '...'
        return '%s %s %s: %s' % (self.content_type.model, self.object_id, author, text)
