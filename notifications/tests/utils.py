from django.core import mail


def _mail_exists(subject, to, strings, html_body):
    for mail_instance in mail.outbox:
        if subject not in mail_instance.subject:
            continue
        if set(mail_instance.to) != set([to]):
            continue
        mail_message = str(mail_instance.message())
        if all(string in mail_message for string in strings):
            if html_body:
                assert html_body in (a[0] for a in mail_instance.alternatives if a[1] == 'text/html')
            else:
                assert not mail_instance.alternatives
            return True
    return False


def check_received_mail_exists(subject, to, strings, clear_outbox=True, html_body=None):
    if not (isinstance(strings, list) or isinstance(strings, tuple)):
        strings = (strings,)
    assert len(mail.outbox) >= 1, "No mails sent"
    assert _mail_exists(subject, to, strings, html_body)
    if clear_outbox:
        mail.outbox = []
