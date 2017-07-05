from django.db import models
from django.utils.translation import ugettext_lazy as _
from parler.models import TranslatableModel, TranslatedFields


NOTIFICATION_TYPES = (
    ('reservation_requested', _("Reservation requested")),

)


class NotificationTemplate(TranslatableModel):
    type = models.CharField(choices=NOTIFICATION_TYPES, max_length=100, unique=True,
                            db_index=True)

    translations = TranslatedFields(
        short_message=models.TextField(help_text=_('Short notification text for e.g. SMS messages')),
        subject=models.CharField(max_length=200, help_text=_('Subject for email notifications')),
        body=models.TextField(help_text=_('Text body for email notifications'))
    )


def render_template(language_code, type, context):
    template = NotificationTemplate.objects.get(type=type, language_code=language_code)
    # return jinja_render()
