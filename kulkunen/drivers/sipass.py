import contextlib
import tempfile
from datetime import datetime, timedelta

import jsonschema
import requests
from cryptography import x509
from cryptography.hazmat.backends import default_backend as crypto_backend
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.crypto import get_random_string

from .base import AccessControlDriver, RemoteError

ACCESS_RULE_TYPES = {
    'access_point_group': 1,
    'access_point': 2,
    'access_level': 3,
    'access_group': 4,
    'venue_booking': 12,
}

DEFAULT_TIME_SCHEDULE_ID = '1'  # Usually (?) maps to "Always"

REQUESTS_TIMEOUT = 30  # seconds


class UnauthorizedError(RemoteError):
    pass


class SiPassAccessRule:
    def __init__(self, target, start_time=None, end_time=None,
                 time_schedule_id=DEFAULT_TIME_SCHEDULE_ID):
        self.target = target
        self.start_time = start_time
        self.end_time = end_time
        self.type = ACCESS_RULE_TYPES[target['type']]
        self.time_schedule_id = time_schedule_id


class SiPassToken:
    value: str
    expires_at: datetime

    def __init__(self, value, expires_at):
        self.value = value
        self.expires_at = expires_at

    def has_expired(self):
        if self.expires_at is None:
            return False
        now = datetime.now()
        if now > self.expires_at + timedelta(seconds=30):
            return True
        return False

    def refresh(self, expiration_time):
        self.expires_at = datetime.now() + timedelta(seconds=expiration_time)

    def serialize(self):
        return dict(value=self.value, expires_at=self.expires_at.timestamp())

    @classmethod
    def deserialize(cls, data):
        try:
            value = data['value']
            expires_at = datetime.fromtimestamp(data['expires_at'])
        except Exception:
            return None
        return SiPassToken(value=value, expires_at=expires_at)


class SiPassDriver(AccessControlDriver):
    token: SiPassToken
    token_expiration_time: int

    SYSTEM_CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "api_url": {
                "type": "string",
                "format": "uri",
                "pattern": "^https?://",
            },
            "username": {
                "type": "string",
            },
            "password": {
                "type": "string",
            },
            "credential_profile_name": {
                "type": "string",
            },
            "cardholder_workgroup_name": {
                "type": "string",
            },
            "client_id": {
                "type": "string",
            },
            "verify_tls": {
                "type": "boolean",
            },
            "tls_ca_cert": {
                "type": "string",
                "format": "textarea",
            },
            "tls_client_cert": {
                "type": "string",
                "format": "textarea",
            },
        },
        "required": [
            "api_url", "username", "password", "credential_profile_name",
            "cardholder_workgroup_name",
        ],
    }
    RESOURCE_CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "access_point_group_name": {
                "type": "string",
            },
            "credential_profile_name": {
                "type": "string",
            }
        },
        "required": [
            "access_point_group_name"
        ]
    }

    DEFAULT_CONFIG = {
        "client_id": "kulkunen",
        "verify_tls": True
    }

    def get_system_config_schema(self):
        return self.SYSTEM_CONFIG_SCHEMA

    def get_resource_config_schema(self):
        return self.RESOURCE_CONFIG_SCHEMA

    def get_resource_identifier(self, resource):
        config = resource.driver_config or {}
        return config.get('access_point_group_name', '')

    def _validate_tls_cert_config(self, config):
        ca_cert = config.get('tls_ca_cert', None)
        if ca_cert:
            try:
                x509.load_pem_x509_certificate(ca_cert.encode('ascii'), crypto_backend())
            except Exception as e:
                raise ValidationError("'tls_ca_cert' must include the certificate in PEM format: \"%s\"" % e)

        client_cert = config.get('tls_client_cert', None)
        if client_cert:
            cert_data = client_cert.encode('ascii')
            try:
                x509.load_pem_x509_certificate(cert_data, crypto_backend())
            except Exception as e:
                raise ValidationError("'tls_client_cert' must include the certificate in PEM format: \"%s\"" % e)
            try:
                load_pem_private_key(cert_data, password=None, backend=crypto_backend())
            except Exception as e:
                raise ValidationError("'tls_client_cert' must include a PEM-encoded private key: \"%s\"" % e)

    def validate_system_config(self, config):
        try:
            jsonschema.validate(config, self.SYSTEM_CONFIG_SCHEMA)
        except jsonschema.exceptions.ValidationError as e:
            raise ValidationError(e.message)

        self._validate_tls_cert_config(config)

    def validate_resource_config(self, resource, config):
        try:
            jsonschema.validate(config, self.RESOURCE_CONFIG_SCHEMA)
        except jsonschema.exceptions.ValidationError as e:
            raise ValidationError(e.message)

    def _save_token(self, token):
        self.update_driver_data(dict(token=token.serialize()))

    def _load_token(self):
        data = self.get_driver_data().get('token')
        return SiPassToken.deserialize(data)

    def api_get_token(self):
        username = self.get_setting('username')
        password = self.get_setting('password')

        data = dict(Username=username, Password=password)
        resp = self.api_req_unauth('authentication', 'POST', data=data)
        if not resp['Token']:
            raise Exception("Username or password incorrect")
        token = SiPassToken(value=resp['Token'], expires_at=None)
        self.logger.info("Token: %s" % token.value)
        return token

    def api_renew_session(self):
        self.api_get('authentication')

    @contextlib.contextmanager
    def ensure_token(self):
        driver_data = self.get_driver_data()
        token_expiration_time = driver_data.get('token_expiration_time')
        token = self._load_token()
        if not token or token.has_expired():
            token = self.api_get_token()

        if not token_expiration_time:
            resp = self.api_req_unauth('authentication/sessiontimeout', 'GET', headers={
                'Authorization': token.value
            })
            if isinstance(resp, int):
                token_expiration_time = resp
            else:
                token_expiration_time = 360  # default
            self.update_driver_data(dict(token_expiration_time=token_expiration_time))

        token.refresh(token_expiration_time)
        self._save_token(token)

        try:
            yield token
        except Exception as e:
            raise

    @contextlib.contextmanager
    def _generate_ca_files(self):
        ca_cert = self.get_setting('tls_ca_cert', True)
        client_cert = self.get_setting('tls_client_cert', True)
        requests_args = {}

        with contextlib.ExitStack() as stack:
            if ca_cert:
                tf = tempfile.NamedTemporaryFile()
                stack.enter_context(tf)
                tf.write(ca_cert.encode('ascii'))
                tf.seek(0)
                requests_args['verify'] = tf.name
            if client_cert:
                tf = tempfile.NamedTemporaryFile()
                tf.write(client_cert.encode('ascii'))
                tf.seek(0)
                stack.enter_context(tf)
                requests_args['cert'] = tf.name
            yield requests_args

    def api_req_unauth(self, path, method, data=None, params=None, headers=None):
        headers = headers.copy() if headers is not None else {}
        headers.update({
            'clientUniqueId': self.get_setting('client_id'),
            'language': 'English'
        })
        verify_tls = self.get_setting('verify_tls')
        url = '%s/%s' % (self.get_setting('api_url'), path)
        self.logger.info('%s: %s' % (method, url))
        args = dict(headers=headers, verify=verify_tls)
        if method == 'POST':
            args['json'] = data
        elif method == 'PUT':
            args['json'] = data
        elif method == 'GET':
            args['params'] = params
        elif method == 'DELETE':
            args['params'] = params
        else:
            raise Exception("Invalid method")

        with self._generate_ca_files() as ca_args:
            args.update(ca_args)
            resp = requests.request(method, url, timeout=REQUESTS_TIMEOUT, **args)

        if resp.status_code not in (200, 201, 204):
            if resp.content:
                try:
                    data = resp.json()
                    err_code = data.get('ErrorCode')
                    err_str = data.get('Message')
                except Exception:
                    err_code = ''
                    err_str = ''
                status_code = resp.status_code
                self.logger.error(f"SiPass API error [HTTP {status_code}] [{err_code}] {err_str}")

            # Clear the object cache just in case, something might've
            # changed in the API.
            self._nuke_object_cache()

            if resp.status_code == 401:
                # If the server responds with "unauthorized", it's possible that
                # the access token is expired (even though it's not supposed to just yet).
                # We nuke the access token and rely on the upper-layer retry mechanism
                # to try again later.
                self.update_driver_data(dict(token=None))

            resp.raise_for_status()

        if not resp.content:
            return None
        return resp.json()

    def api_get(self, path, params=None):
        with self.ensure_token() as token:
            resp = self.api_req_unauth(path, 'GET', params=params, headers={
                'Authorization': token.value
            })
        return resp

    def api_post(self, path, data):
        with self.ensure_token() as token:
            resp = self.api_req_unauth(path, 'POST', data, headers={
                'Authorization': token.value
            })
        return resp

    def api_put(self, path, data):
        with self.ensure_token() as token:
            resp = self.api_req_unauth(path, 'PUT', data, headers={
                'Authorization': token.value
            })
        return resp

    def api_delete(self, path):
        with self.ensure_token() as token:
            resp = self.api_req_unauth(path, 'DELETE', headers={
                'Authorization': token.value
            })
        return resp

    def get_cardholders(self):
        params = {
            'searchString': '',
            'appId': 'Cardholders',
            'fields': 'FirstName,LastName,Status',
            'sortingOrder': '{"FieldName":"LastName","Value":"","SortingOrder":0}',
            'filterExpression': "{'Identifier': ''}",
            'startIndex': 0,
            'endIndex': 100,
        }
        resp = self.api_get('Cardholders', params=params)
        return [dict(
            id=d['Token'],
            status=d['Status'],
            first_name=d['FirstName'],
            last_name=d['LastName']
        ) for d in resp['Records']]

    def get_cardholder(self, cardholder_id):
        return self.api_get('Cardholders/%s' % cardholder_id)

    def get_access_levels(self):
        resp = self.api_get('AccessLevels')
        records = [dict(name=r['Name'], id=r['Token'], type='access_level') for r in resp['Records']]
        return records

    def get_access_point_groups(self):
        resp = self.api_get('AccessPointGroups')
        records = [dict(name=r['Name'], id=r['Token'], type='access_point_group') for r in resp['Records']]
        return records

    def get_workgroups(self):
        resp = self.api_get('WorkGroups')
        records = [dict(name=r['Name'], id=r['Token']) for r in resp['Records']]
        return records

    def get_time_schedules(self):
        resp = self.api_get('TimeSchedules')
        if isinstance(resp, dict) and 'Records' in resp:
            resp = resp['Records']
        return [dict(id=d['Token'], name=d['Name']) for d in resp]

    def get_card_technologies(self):
        resp = self.api_get('CardTechnologies')
        if isinstance(resp, dict) and 'Records' in resp:
            resp = resp['Records']
        return [dict(
            id=d['TechnologyCode'],
            name=d['Name'],
            facility_code_digits=d.get('FacilityCodeDigits', None),
            card_number_digits=d.get('CardNumberDigits', None)
        ) for d in resp]

    def get_credential_profiles(self):
        resp = self.api_get('CredentialProfiles')
        if isinstance(resp, dict) and 'Records' in resp:
            resp = resp['Records']
        return [dict(
            id=d.pop('Token'),
            name=d.pop('Name'),
            card_technology_id=d.pop('CardTechnologyCode'),
            card_technology_name=d.pop('CardTechnology'),
            **d
        ) for d in resp]

    def _refresh_objects(self, object_type):
        """Loads named objects from SiPass API and saves them in the database"""
        object_get_func = getattr(self, 'get_%s' % object_type)
        objs = {x['name']: x for x in object_get_func()}

        with self.system_lock() as system:
            driver_data = system.driver_data or {}
            object_cache = driver_data.setdefault('object_cache', {})
            object_cache[object_type] = objs
            system.driver_data = driver_data
            system.save(update_fields=['driver_data'])
        return objs

    def _nuke_object_cache(self):
        with self.system_lock() as system:
            driver_data = system.driver_data or {}
            if driver_data.get('object_cache'):
                driver_data['object_cache'] = {}
                system.save(update_fields=['driver_data'])

    def get_object_by_id(self, grant, object_type, setting_name):
        """Returns the API object corresponding to an object name

        The object name is taken from either the resource config, or if not found,
        the system-level config. If the object is not in the system-level object
        cache, the objects are refreshed from the API.
        """
        obj_name = grant.resource.driver_config.get(setting_name, None)
        if not obj_name:
            obj_name = self.get_setting(setting_name)

        objs = self.get_driver_data().get('object_cache', {}).get(object_type, {})
        if obj_name not in objs:
            objs = self._refresh_objects(object_type)
        obj = objs.get(obj_name)
        if obj is None:
            raise RemoteError("[%s] Invalid %s name: %s" % (grant, object_type, obj_name))
        return obj

    def remove_cardholder(self, cardholder_id):
        self.api_delete('Cardholders/%s' % cardholder_id)

    def _generate_access_rule(self, access_rule):
        ar = access_rule
        ar_start = ar.start_time
        if ar_start:
            ar_start = ar_start.replace(microsecond=0).isoformat()
        ar_end = ar.end_time
        if ar_end:
            ar_end = ar_end.replace(microsecond=0).isoformat()

        target = ar.target
        out = {
            'ArmingRightsId': None,
            'ControlModeId': None,
            'EndDate': ar_end,
            'ObjectName': target['name'],
            'ObjectToken': '-1',
            'RuleToken': target['id'],
            'RuleType': ar.type,
            'StartDate': ar_start,
            'Side': 0,
            'TimeScheduleToken': ar.time_schedule_id,
        }
        return out

    def api_create_cardholder(self, data):
        required_keys = [
            'first_name', 'last_name', 'card_number', 'pin', 'credential_profile',
            'workgroup'
        ]
        for key in required_keys:
            assert key in data, "Key '%s' needed" % key

        # Compensate for possible clock drift
        now = timezone.now() - timedelta(minutes=10)

        ar_list = data.get('access_rules', [])
        if ar_list:
            start_time = min([x.start_time for x in ar_list])
            end_time = max([x.end_time for x in ar_list])
        else:
            start_time = data.get('start_time', now)
            end_time = start_time + timedelta(days=1)

        access_rules = []
        for ar in ar_list:
            access_rules.append(self._generate_access_rule(ar))

        start_time = start_time.replace(microsecond=0)
        end_time = end_time.replace(microsecond=0)

        credentials = {
            'CardNumber': data['card_number'],
            'CardTechnologyCode': data['card_technology_id'],
            'EndDate': end_time.isoformat(),
            'FacilityCode': 0,
            'Pin': data['pin'],
            'PinMode': data['credential_profile']['PINModeValue']['Type'],
            'ProfileId': data['credential_profile']['id'],
            'ProfileName': data['credential_profile']['name'],
            'StartDate': start_time.isoformat(),
            'RevisionNumber': 0,
        }

        # All of these keys must be present, otherwise the POST request
        # will fail with HTTP 500...
        cardholder_data = {
            'AccessRules': access_rules,
            'ApbWorkgroupId': data['workgroup']['id'],
            'Attributes': {
                'Accessibility': False,
                'ApbExclusion': False,
                'ApbReEntryExclusion': False,
                'Isolate': False,
                'SelfAuthorize': False,
                'Supervisor': False,
                'Visitor': False,
                'Void': False,
            },
            'BaseCardNumber': None,
            'Credentials': [credentials],
            'EmployeeNumber': '',
            'EmployeeName': None,
            'EndDate': end_time.isoformat(),
            'FingerPrints': [],
            'FirstName': data['first_name'],
            'GeneralInformation': '',
            'LastName': data['last_name'],
            'NonPartitionWorkGroups': [],
            'NonPartitionWorkgroupAccessRules': [],
            'PersonalDetails': {
                'Address': '',
                'ContactDetails': {
                    'Email': '',
                    'MobileNumber': '',
                    'MobileServiceProviderId': '0',
                    'PagerNumber': '',
                    'PagerServiceProviderId': '0',
                    'PhoneNumber': ''
                },
                'DateOfBirth': '',
                'PayrollNumber': '',
                'Title': '',
                'UserDetails': {
                    'Password': '',
                    'UserName': ''
                }
            },
            'Potrait': None,
            'PrimaryWorkgroupId': data['workgroup']['id'],
            'PrimaryWorkgroupName': data['workgroup']['name'],
            'SmartCardProfileId': '0',
            'SmartCardProfileName': None,
            'StartDate': start_time.isoformat(),
            'Status': 61,  # 61 means Valid
            'Token': '-1',
            'TraceDetails': {
                'CardLastUsed': None,
                'CardNumberLastUsed': None,
                'LastApbLocation': None,
                'PointName': None,
                'TraceCard': False
            },
            'Vehicle1': {
                'CarColor': '',
                'CarModelNumber': '',
                'CarRegistrationNumber': ''
            },
            'Vehicle2': {
                'CarColor': '',
                'CarModelNumber': '',
                'CarRegistrationNumber': ''
            },
            'VisitorDetails': {
                'VisitedEmployeeFirstName': '',
                'VisitedEmployeeLastName': '',
                'VisitorCardStatus': 0,
                'VisitorCustomValues': {}
            }
        }
        resp = self.api_post('Cardholders', data=cardholder_data)
        cardholder_id = resp['Token']

        return cardholder_id

    def create_access_user(self, grant):
        user = grant.reservation.user
        # Make sure there is something in first_name and last_name
        first_name = user.first_name or 'Kulkunen'
        last_name = user.last_name or 'Kulkunen'

        # We lock the access control instance through the database to protect
        # against race conditions.
        with self.system_lock():
            # The PIN also serves as the cardholder identifier (they must
            # be identical). Try at most 20 times to generate an unused PIN,
            # and if that fails, we probably have other problems. Upper layers
            # will take care of retrying later in case the unlikely false positive
            # happens.
            for i in range(20):
                pin = get_random_string(1, '123456789') + get_random_string(3, '0123456789')
                if not self.system.users.active().filter(identifier=pin).exists():
                    break
            else:
                raise RemoteError("Unable to find a PIN code for grant")

            user_attrs = dict(identifier=pin, first_name=first_name, last_name=last_name, user=user)
            user = self.system.users.create(**user_attrs)

        return user

    def create_cardholder(self, grant, user):
        start_time = grant.starts_at
        end_time = grant.ends_at

        access_point_group = self.get_object_by_id(grant, 'access_point_groups', 'access_point_group_name')
        access_rule = SiPassAccessRule(access_point_group, start_time, end_time)

        credential_profile = self.get_object_by_id(grant, 'credential_profiles', 'credential_profile_name')
        workgroup = self.get_object_by_id(grant, 'workgroups', 'cardholder_workgroup_name')
        card_technology_id = credential_profile['card_technology_id']

        cardholder_id = self.api_create_cardholder(dict(
            first_name=user.first_name,
            last_name=user.last_name,
            card_number=user.identifier,
            pin=user.identifier,
            access_rules=[access_rule],
            card_technology_id=card_technology_id,
            credential_profile=credential_profile,
            workgroup=workgroup,
        ))

        return cardholder_id

    def install_grant(self, grant):
        self.logger.info('[%s] Installing SiPass grant' % grant)

        assert grant.state == grant.INSTALLING

        user = self.create_access_user(grant)

        try:
            cardholder_id = self.create_cardholder(grant, user)
        except Exception as e:
            user.delete()
            raise

        self.logger.info('[%s] Cardholder created with ID %s and PIN %s' % (grant, cardholder_id, user.identifier))

        user.driver_data = dict(cardholder_id=cardholder_id)
        user.save(update_fields=['driver_data'])
        grant.access_code = user.identifier
        grant.user = user
        grant.state = grant.INSTALLED
        grant.remove_at = grant.ends_at
        grant.save(update_fields=['user', 'state', 'access_code', 'remove_at'])
        grant.notify_access_code()

    def remove_grant(self, grant):
        self.logger.info('[%s] Removing SiPass grant' % grant)

        assert grant.state == grant.REMOVING

        user = grant.user
        cardholder_id = user.driver_data['cardholder_id']
        self.remove_cardholder(user.driver_data['cardholder_id'])

        user.state = user.REMOVED
        user.removed_at = timezone.now()
        user.save(update_fields=['state', 'removed_at'])

        grant.state = grant.REMOVED
        grant.removed_at = user.removed_at
        grant.save(update_fields=['state', 'removed_at'])

        self.logger.info('[%s] Cardholder with ID %s and PIN %s removed' % (grant, cardholder_id, user.identifier))

    def prepare_install_grant(self, grant):
        # Because of a bug in SiPass API, the changes are not synchronized
        # to the building units automatically. We install the grants one day
        # before their start time and schedule a re-install of the units
        # every nightly.
        grant.install_at = grant.starts_at - timedelta(days=1)
        grant.save(update_fields=['install_at'])

    def save_respa_resource(self, resource, respa_resource):
        # SiPass driver generates access codes by itself, so we need to
        # make sure Respa doesn't generate them.
        if not respa_resource.generate_access_codes:
            return
        respa_resource.generate_access_codes = False

    def save_resource(self, resource):
        # SiPass driver generates access codes by itself, so we need to
        # make sure Respa doesn't generate them.
        respa_resource = resource.resource
        if not respa_resource.generate_access_codes:
            return
        respa_resource.generate_access_codes = False
        respa_resource.save(update_fields=['generate_access_codes'])
