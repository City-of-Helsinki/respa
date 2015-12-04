import base64
import datetime
import struct
import time

import arrow
from django.conf import settings
from django.utils import timezone
from django.utils.translation import ungettext
from django.template.loader import render_to_string
from django.core.mail import send_mail


DEFAULT_LANG = settings.LANGUAGES[0][0]


def save_dt(obj, attr, dt, orig_tz="UTC"):
    """
    Sets given field in an object to a DateTime object with or without
    a time zone converted into UTC time zone from given time zone

    If there is no time zone on the given DateTime, orig_tz will be used
    """
    if dt.tzinfo:
        arr = arrow.get(dt).to("UTC")
    else:
        arr = arrow.get(dt, orig_tz).to("UTC")
    setattr(obj, attr, arr.datetime)


def get_dt(obj, attr, tz):
    return arrow.get(getattr(obj, attr)).to(tz).datetime


def get_translated(obj, attr):
    key = "%s_%s" % (attr, DEFAULT_LANG)
    val = getattr(obj, key, None)
    if not val:
        val = getattr(obj, attr)
    return val


# Needed for slug fields populating
def get_translated_name(obj):
    return get_translated(obj, 'name')


def generate_id():
    t = time.time() * 1000000
    b = base64.b32encode(struct.pack(">Q", int(t)).lstrip(b'\x00')).strip(b'=').lower()
    return b.decode('utf8')


def time_to_dtz(time, date=None, arr=None):
    tz = timezone.get_current_timezone()
    if time:
        if date:
            return tz.localize(datetime.datetime.combine(date, time))
        elif arr:
            return tz.localize(datetime.datetime(arr.year, arr.month, arr.day, time.hour, time.minute))
    else:
        return None


def is_valid_time_slot(time, time_slot_duration, opening_time):
    """
    Check if given time is correctly aligned with time slots.

    :type time: datetime.datetime
    :type time_slot_duration: datetime.timedelta
    :type opening_time: datetime.datetime
    :rtype: bool
    """
    return not ((time - opening_time) % time_slot_duration)


def humanize_duration(duration):
    """
    Return the given duration in a localized humanized form.

    Examples: "2 hours 30 minutes", "1 hour", "30 minutes"

    :type duration: datetime.timedelta
    :rtype: str
    """
    hours = duration.days * 24 + duration.seconds // 3600
    mins = duration.seconds // 60 % 60
    hours_string = ungettext('%(count)d hour', '%(count)d hours', hours) % {'count': hours} if hours else None
    mins_string = ungettext('%(count)d minute', '%(count)d minutes', mins) % {'count': mins} if mins else None
    return ' '.join(filter(None, (hours_string, mins_string)))


def send_respa_mail(user, subject, message):
    """
    Send a mail containing common Respa extras and given message to given user.

    :type user: User
    :type subject: str
    :type message: str
    """
    final_message = render_to_string('mail/base_message.txt', {'user': user, 'content': message})
    final_subject = render_to_string('mail/base_subject.txt', {'subject': subject})
    send_mail(final_subject, final_message, 'info@respa.com', [user.email])
