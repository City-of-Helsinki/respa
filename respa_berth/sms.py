
# -*- coding: utf-8 -*-
"""SMS API"""

import logging


import twilio
from twilio.rest import TwilioRestClient
from twilio.rest import Client
from django.conf import settings
from twilio.base.exceptions import TwilioRestException
from respa_berth.models.sms_message import SMSMessage

LOG = logging.getLogger(__name__)


def send_sms(phone_number, msg, reservation, sms=None):
  if settings.DEBUG:
    LOG.info('In debug mode. Not sending SMS')
    return

  def _check_twilio_setting(setting_name):
    return hasattr(settings, setting_name) and bool(getattr(settings, setting_name))

  for s in ['TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_FROM_NUMBER']:
    if not _check_twilio_setting(s):
      LOG.error('Twilio setting %s missing or not correct. Can not send sms' % s)
      return

  LOG.debug('sending sms to %s  ' % (phone_number))
  client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

  callback_url = 'https://varaukset.hameenlinna.fi/api/sms/'
  if settings.DEBUG:
    callback_url = 'https://varaukset.haltudemo.fi/api/sms/'

  if sms and hasattr(sms, 'twilio_id') and sms.twilio_id:
    try:
      twilio_sms = client.messages(sms.twilio_id).fetch()
      if twilio_sms.status == 'delivered':
        sms.success = True
        sms.save()
        return
      if twilio_sms.status in ['sent', 'queued', 'accepted'] or twilio_sms.error_code == 30003:
        return

    except:
      LOG.exception('Previously saved sms message not found from twilio %s' % repr(phone_number))
      pass

  if not sms:
    sms = SMSMessage.objects.create(
      message_body=str(msg),
      to_phone_number=str(phone_number),
      berth_reservation=reservation
    )

  try:
    twilio_sms = client.messages.create(
      body=str(msg),
      to=str(phone_number),
      from_=settings.TWILIO_FROM_NUMBER,
      status_callback=callback_url
    )

    sms.twilio_id = twilio_sms.sid
    if twilio_sms.status == 'delivered':
      sms.success = True
    sms.save()

  except:
    LOG.exception('Could not send sms to number %s' % repr(phone_number))
    pass

# vim: tabstop=2 expandtab shiftwidth=2 softtabstop=2
