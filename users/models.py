from django.db import models
from helusers.models import AbstractUser
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from resources.models import Resource


class User(AbstractUser):
    ical_token = models.SlugField(
        max_length=16, null=True, blank=True, unique=True, db_index=True, verbose_name="iCal token"
    )
    preferred_language = models.CharField(max_length=8, null=True, blank=True,
                                          verbose_name="Preferred UI language",
                                          choices=settings.LANGUAGES)
    favorite_resources = models.ManyToManyField(Resource, blank=True, verbose_name=_('Favorite resources'),
                                                related_name='favorited_by')

    # Duplicate the is staff field from the abstract base class to here
    # so that we can override the verbose name and help text.
    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
        help_text=_(
            "Designates whether the user can log into "
            "Django Admin or Respa Admin sites."))

    is_general_admin = models.BooleanField(
        default=False, verbose_name=_("general administrator status"),
        help_text=_(
            "Designates whether the user is a General Administrator "
            "with special permissions to many objects within Respa. "
            "This is almost as powerful as superuser."))

    class Meta:
        ordering = ('id',)

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
