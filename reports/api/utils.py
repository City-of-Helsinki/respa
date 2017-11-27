from rest_framework import fields


DATETIME_FIELD = fields.DateTimeField()


def iso_to_dt(iso):
    return DATETIME_FIELD.to_internal_value(iso)
