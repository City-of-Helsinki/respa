from django.core.exceptions import ValidationError


class InvalidImage(ValidationError):
    pass
