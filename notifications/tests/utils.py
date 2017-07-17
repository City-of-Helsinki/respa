from django.core import mail


def _mail_exists(subject, to, strings):
    for mail_instance in mail.outbox:
        if subject not in mail_instance.subject:
            continue
        if set(mail_instance.to) != set([to]):
            continue
        mail_message = str(mail_instance.message())
        if not all(string in mail_message for string in strings):
            continue
        return True
    return False


def check_received_mail_exists(subject, to, strings, clear_outbox=True):
    if not (isinstance(strings, list) or isinstance(strings, tuple)):
        strings = (strings,)
    assert _mail_exists(subject, to, strings)
    if clear_outbox:
        mail.outbox = []
