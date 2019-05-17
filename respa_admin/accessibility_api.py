
# -*- coding: utf-8 -*-

import datetime
from hashlib import sha256
from urllib.parse import quote


def generate_url(api_url, system_id, target_id, target_name, user, secret, form_id='2', lang='fi', location_id=None):
    url = '{api_url}app/{lang}/target/'.format(api_url=api_url, lang=lang)
    valid_until = datetime.datetime.now() + datetime.timedelta(days=2)
    valid_until_iso8601 = valid_until.isoformat(timespec='seconds')
    url_params = {
        'systemId': system_id,
        'targetId': target_id,
        'user': user,
        'validUntil': valid_until_iso8601,
        'name': target_name,
        'formId': form_id,
    }
    if location_id is not None:
        url_params['locationId'] = location_id
    url_params['checksum'] = calculate_checksum(url_params, secret)
    return '{}?{}'.format(url, '&'.join(['{}={}'.format(key, quote(val)) for key, val in url_params.items()]))


def calculate_checksum(params, secret):
    checksum_params = params.copy()
    if 'locationId' not in checksum_params:
        checksum_params['locationId'] = ''
    payload = str(secret) + '{systemId}{targetId}{locationId}{user}{validUntil}{name}{formId}'.format(**checksum_params)
    return sha256(payload.encode('utf8')).hexdigest().upper()
