import re

_WORD_CHAR_RX = re.compile(r'\w')


def sanitize_replace_with_xxx(value):
    if not value:
        return value
    return _WORD_CHAR_RX.sub('x', value)
