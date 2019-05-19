import base64
import datetime
import struct
import time
import io
import logging

import arrow
from django.conf import settings
from django.utils import formats
from django.utils.translation import ungettext
from django.core.mail import EmailMultiAlternatives
from django.contrib.sites.models import Site
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.utils.timezone import localtime
from rest_framework.reverse import reverse
from icalendar import Calendar, Event, vDatetime, vText, vGeo
import xlsxwriter


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


notification_logger = logging.getLogger('respa.notifications')


def send_respa_mail(email_address, subject, body, html_body=None, attachments=None):
    if not getattr(settings, 'RESPA_MAILS_ENABLED', False):
        return

    from_address = (getattr(settings, 'RESPA_MAILS_FROM_ADDRESS', None) or
                    'noreply@%s' % Site.objects.get_current().domain)

    notification_logger.info('Sending notification email to %s: "%s"' % (email_address, subject))

    text_content = body
    msg = EmailMultiAlternatives(subject, text_content, from_address, [email_address], attachments=attachments)
    if html_body:
        msg.attach_alternative(html_body, 'text/html')
    msg.send()


def generate_reservation_xlsx(reservations):
    """
    Return reservations in Excel xlsx format

    The parameter is expected to be a list of dicts with fields:
      * unit: unit name str
      * resource: resource name str
      * begin: begin time datetime
      * end: end time datetime
      * staff_event: is staff event bool
      * user: user email str (optional)
      * comments: comments str (optional)

    :rtype: bytes
    """
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet()

    headers = (
        ('Unit', 30),
        ('Resource', 30),
        ('Begin time', 15),
        ('End time', 15),
        ('Created at', 15),
        ('User', 30),
        ('Comments', 30),
        ('Staff event', 10),
    )
    header_format = workbook.add_format({'bold': True})
    for column, header in enumerate(headers):
        worksheet.write(0, column, str(_(header[0])), header_format)
        worksheet.set_column(column, column, header[1])

    date_format = workbook.add_format({'num_format': 'dd.mm.yyyy hh:mm', 'align': 'left'})
    for row, reservation in enumerate(reservations, 1):
        worksheet.write(row, 0, reservation['unit'])
        worksheet.write(row, 1, reservation['resource'])
        worksheet.write(row, 2, localtime(reservation['begin']).replace(tzinfo=None), date_format)
        worksheet.write(row, 3, localtime(reservation['end']).replace(tzinfo=None), date_format)
        worksheet.write(row, 4, localtime(reservation['created_at']).replace(tzinfo=None), date_format)
        if 'user' in reservation:
            worksheet.write(row, 5, reservation['user'])
        if 'comments' in reservation:
            worksheet.write(row, 6, reservation['comments'])
        worksheet.write(row, 7, reservation['staff_event'])
    workbook.close()
    return output.getvalue()


def get_object_or_none(cls, **kwargs):
    try:
        return cls.objects.get(**kwargs)
    except cls.DoesNotExist:
        return None


def create_datetime_days_from_now(days_from_now):
    if days_from_now is None:
        return None

    dt = timezone.now() + datetime.timedelta(days=days_from_now + 1)
    dt = dt.replace(hour=0, minute=0, second=0, microsecond=0)

    return dt


def localize_datetime(dt):
    return formats.date_format(timezone.localtime(dt), 'DATETIME_FORMAT')


def format_dt_range(language, begin, end):
    if language == 'fi':
        # ma 1.1.2017 klo 12.00
        begin_format = r'D j.n.Y \k\l\o G.i'
        if begin.date() == end.date():
            end_format = 'G.i'
            sep = '–'
        else:
            end_format = begin_format
            sep = ' – '

        res = sep.join([formats.date_format(begin, begin_format), formats.date_format(end, end_format)])
    else:
        # default to English
        begin_format = r'D j/n/Y G:i'
        if begin.date() == end.date():
            end_format = 'G:i'
            sep = '–'
        else:
            end_format = begin_format
            sep = ' – '

        res = sep.join([formats.date_format(begin, begin_format), formats.date_format(end, end_format)])

    return res


def build_reservations_ical_file(reservations):
    """
    Return iCalendar file containing given reservations
    """

    cal = Calendar()
    cal['X-WR-CALNAME'] = vText('RESPA')
    cal['name'] = vText('RESPA')
    for reservation in reservations:
        event = Event()
        event['uid'] = 'respa_reservation_{}'.format(reservation.id)
        event['dtstart'] = vDatetime(reservation.begin)
        event['dtend'] = vDatetime(reservation.end)
        unit = reservation.resource.unit
        event['location'] = vText('{} {} {}'.format(unit.name, unit.street_address, unit.address_zip))
        if unit.location:
            event['geo'] = vGeo(unit.location)
        event['summary'] = vText('{} {}'.format(unit.name, reservation.resource.name))
        cal.add_component(event)
    return cal.to_ical()


def build_ical_feed_url(ical_token, request):
    """
    Return iCal feed url for given token without query parameters
    """

    url = reverse('ical-feed', kwargs={'ical_token': ical_token}, request=request)
    return url[:url.find('?')]
