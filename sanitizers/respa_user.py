from database_sanitizer.sanitizers import user as base


def sanitize_username(value):
    """
    Sanitize Respa username.

    None, empty string and AnonymousUser will be returned as is.
    Otherwise a sanitized value is generated.

    >>> sanitize_username('')
    ''

    >>> sanitize_username(None)

    >>> sanitize_username('AnonymousUser')
    'AnonymousUser'

    >>> assert sanitize_username('john-doe') != 'john-doe'
    """
    if not value or value == 'AnonymousUser':
        return value
    return base.sanitize_username(value)
