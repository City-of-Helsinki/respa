import re

_WORD_CHAR_RX = re.compile(r'\w')


def sanitize_replace_with_xxx(value):
    """
    Sanitize a string value by replacing it with x's.

    >>> sanitize_replace_with_xxx('')
    ''

    >>> sanitize_replace_with_xxx(None)

    >>> sanitize_replace_with_xxx('Hello')
    'xxxxx'

    >>> sanitize_replace_with_xxx('Hello Sanitized World!')
    'xxxxx xxxxxxxxx xxxxx!'
    """
    if not value:
        return value
    return _WORD_CHAR_RX.sub('x', value)
