from django.db import models
from helusers.models import AbstractUser


class User(AbstractUser):
    def get_display_name(self):
        return '{0} {1}'.format(self.first_name, self.last_name).strip()
