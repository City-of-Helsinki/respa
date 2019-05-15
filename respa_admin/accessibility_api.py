
# -*- coding: utf-8 -*-

import datetime
from hashlib import sha256
from urllib.parse import quote


def generate_url(api_url, system_id, target_id, target_name, user, secret, form_id="2", lang="fi"):
    url = '{api_url}app/{lang}/target/'.format(api_url=api_url, lang=lang)
    valid_until = datetime.datetime.now() + datetime.timedelta(days=2)
    valid_until_iso8601 = valid_until.isoformat(timespec='seconds')
    url_params = {
        "systemId": system_id,
        "targetId": target_id,
        "user": user,
        "validUntil": valid_until_iso8601,
        "name": target_name,
        "formId": form_id,
    }
    url_params.update({"checksum": calculate_checksum(url_params, secret)})
    return "{}?{}".format(url, "&".join(["{}={}".format(key, quote(val)) for key, val in url_params.items()]))


def calculate_checksum(params, secret):
    payload = str(secret) + "{systemId}{targetId}{user}{validUntil}{name}{formId}".format(**params)
    return sha256(payload.encode('utf8')).hexdigest().upper()
