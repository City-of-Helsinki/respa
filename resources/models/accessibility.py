from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext as _
from .base import AutoIdentifiedModel
from .resource import Resource


class AccessibilityViewpoint(AutoIdentifiedModel):
    id = models.CharField(primary_key=True, max_length=50)
    name = models.CharField(verbose_name=_('Name'), max_length=200)
    # ordering is text based in the accessibility api
    order_text = models.CharField(verbose_name=_('Order'), max_length=200, default="0")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Time of creation'))
    modified_at = models.DateTimeField(auto_now=True, verbose_name=_('Time of modification'))

    class Meta:
        verbose_name = _('accessibility viewpoint')
        verbose_name_plural = _('accessibility viewpoints')
        ordering = ('order_text',)

    def __str__(self):
        return self.name


class AccessibilityValue(AutoIdentifiedModel):
    UNKNOWN_ORDERING = 0
    value = models.CharField(max_length=128, unique=True, verbose_name=_('Accessibility summary value'))
    order = models.IntegerField(verbose_name=_('Ordering priority'), default=UNKNOWN_ORDERING)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Time of creation'))
    modified_at = models.DateTimeField(auto_now=True, verbose_name=_('Time of modification'))

    class Meta:
        ordering = ('order',)
        verbose_name = _('accessibility value')
        verbose_name_plural = _('accessibility values')

    def save(self, *args, **kwargs):
        """ Update the cached ordering of related ResourceAccessibility objects """
        if self.id:
            ResourceAccessibility.objects.filter(value=self).update(order=self.order)
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.value


class ResourceAccessibility(AutoIdentifiedModel):
    viewpoint = models.ForeignKey(AccessibilityViewpoint, related_name='accessibility_summaries',
                                  verbose_name=_('Resource Accessibility'), on_delete=models.CASCADE)
    resource = models.ForeignKey(Resource, related_name='accessibility_summaries', verbose_name=_('Resource'),
                                 db_index=True, on_delete=models.CASCADE)
    value = models.ForeignKey(AccessibilityValue, verbose_name=_('Accessibility summary value'),
                              on_delete=models.CASCADE)
    order = models.IntegerField(verbose_name=_('Resource ordering priority'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Time of creation'))
    modified_at = models.DateTimeField(auto_now=True, verbose_name=_('Time of modification'))

    class Meta:
        ordering = ('id',)
        unique_together = ('viewpoint', 'resource')
        verbose_name = _('resource accessibility summary')
        verbose_name_plural = _('resource accessibility summaries')

    def save(self, *args, **kwargs):
        self.order = self.value.order
        return super().save(*args, **kwargs)

    def __str__(self):
        return '{} / {}: {}'.format(self.resource, self.viewpoint, self.value)
