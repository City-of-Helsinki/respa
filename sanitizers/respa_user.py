from database_sanitizer.sanitizers import user as base


def sanitize_username(value):
    if not value or value == 'AnonymousUser':
        return value
    return base.sanitize_username(value)
