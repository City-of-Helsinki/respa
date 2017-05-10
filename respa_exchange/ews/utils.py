from pytz import utc

EXCHANGE_DATETIME_FORMAT = u"%Y-%m-%dT%H:%M:%SZ"


def as_utc(instant):
    """
    Convert a datetime to UTC.

    :param instant: The datetime to convert
    :return: Datetime in UTC.
    """
    if instant.tzinfo:
        return instant.astimezone(utc)
    return utc.localize(instant)


def format_date_for_xml(instant):
    """
    Format a date in the format expected by EWS (ISO 8601, zulu time)

    :param instant: The date to format
    :return: Formatted string
    :rtype: str
    """
    return as_utc(instant).strftime(EXCHANGE_DATETIME_FORMAT)
