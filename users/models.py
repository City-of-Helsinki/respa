from django.db import models
from helusers.models import AbstractUser
from django.utils.crypto import get_random_string
from django.conf import settings


class User(AbstractUser):
    ical_token = models.SlugField(
        max_length=16, null=True, blank=True, unique=True, db_index=True, verbose_name="iCal token"
    )
    preferred_language = models.CharField(max_length=8, null=True, blank=True,
                                          verbose_name="Preferred UI language",
                                          choices=settings.LANGUAGES)

    def get_display_name(self):
        return '{0} {1}'.format(self.first_name, self.last_name).strip()

    def get_or_create_ical_token(self, recreate=False):
        if not self.ical_token or recreate:
            self.ical_token = get_random_string(length=16)
            self.save()
        return self.ical_token

    def get_preferred_language(self):
        if not self.preferred_language:
            return settings.LANGUAGES[0][0]
        else:
            return self.preferred_language
