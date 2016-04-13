from datetime import datetime

from pytz import utc

EXCHANGE_DATETIME_FORMAT = u"%Y-%m-%dT%H:%M:%SZ"


def as_utc(datetime_to_convert):
    if datetime_to_convert.tzinfo:
        return datetime_to_convert.astimezone(utc)
    else:
        return utc.localize(datetime_to_convert)


def format_date_for_xml(datetime_or_date):
    if isinstance(datetime_or_date, datetime):
        return as_utc(datetime_or_date).strftime(EXCHANGE_DATETIME_FORMAT)

    raise TypeError("Not sure how to format %r" % datetime_or_date)  # pragma: no cover
