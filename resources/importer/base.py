import base64
import logging
import os
import re
import struct
import time
import functools

from django.conf import settings
from modeltranslation.translator import translator

from resources.models import Resource, Unit, UnitIdentifier
from munigeo.models import Municipality


@functools.lru_cache()
def get_muni(muni_id):
    return Municipality.objects.get(id=muni_id)


class Importer(object):

    @staticmethod
    def clean_text(text):
        text = text.replace('\n', ' ')
        # remove consecutive whitespaces
        return re.sub(r'\s\s+', ' ', text, re.U).strip()

    def find_data_file(self, data_file):
        for path in self.data_paths:
            full_path = os.path.join(path, data_file)
            if os.path.exists(full_path):
                return full_path
        raise FileNotFoundError("Data file '%s' not found" % data_file)

    def _set_field(self, obj, field_name, val):
        if not hasattr(obj, field_name):
            print("'%s' not there!" % field_name)
            print(vars(obj))

        obj_val = getattr(obj, field_name)
        if obj_val == val:
            return

        field = obj._meta.get_field(field_name)
        if field.get_internal_type() == 'CharField' and val is not None:
            if len(val) > field.max_length:
                raise Exception("field '%s' too long (max. %d): %s" % field_name, field.max_length, val)

        setattr(obj, field_name, val)
        obj._changed = True
        obj._changed_fields.append(field_name)

    def _update_fields(self, obj, info, skip_fields):
        obj_fields = list(obj._meta.fields)
        trans_fields = translator.get_options_for_model(type(obj)).fields
        for field_name, lang_fields in trans_fields.items():
            lang_fields = list(lang_fields)
            for lf in lang_fields:
                lang = lf.language
                # Do not process this field later
                skip_fields.append(lf.name)

                if field_name not in info:
                    continue

                data = info[field_name]
                if data is not None and lang in data:
                    val = data[lang]
                else:
                    val = None
                self._set_field(obj, lf.name, val)

            # Remove original translated field
            skip_fields.append(field_name)

        for d in skip_fields:
            for f in obj_fields:
                if f.name == d:
                    obj_fields.remove(f)
                    break

        for field in obj_fields:
            field_name = field.name
            if field.get_internal_type() == 'ForeignKey':
                field_name = "%s_id" % field_name
            if field_name not in info:
                continue
            self._set_field(obj, field_name, info[field_name])

    def _generate_id(self):
        t = time.time() * 1000000
        b = base64.b32encode(struct.pack(">Q", int(t)).lstrip(b'\x00')).strip(b'=').lower()
        return b.decode('utf8')

    def save_unit(self, data, obj):
        if not obj:
            obj = Unit()
            obj._created = True
        else:
            obj._created = False
            obj._changed = False
        obj._changed_fields = []

        self._update_fields(obj, data, ['id', 'identifiers', 'municipality'])

        obj.id = data.get('id')
        if not obj.id:
            obj.id = self._generate_id()

        muni_id = data.get('municipality')
        if muni_id:
            obj.municipality = get_muni(muni_id)

        if obj._created:
            print("%s created" % obj)
            obj.save()

        identifiers = {x.namespace: x for x in obj.identifiers.all()}
        for id_data in data.get('identifiers', []):
            ns = id_data['namespace']
            val = id_data['value']
            if ns in identifiers:
                id_obj = identifiers[ns]
                if id_obj.value != val:
                    id_obj.value = val
                    id_obj.save()
                    obj._changed = True
            else:
                id_obj = UnitIdentifier(unit=obj, namespace=ns, value=val)
                id_obj.save()
                obj._changed = True

        if obj._changed:
            if not obj._created:
                print("%s changed: %s" % (obj, ', '.join(obj._changed_fields)))
            obj.save()

        return obj

    def save_resource(self, data, obj):
        if not obj:
            obj = Resource()
            obj._created = True
        else:
            obj._created = False
            obj._changed = False
        obj._changed_fields = []

        self._update_fields(obj, data, ['id', 'purposes'])

        if obj._created:
            print("%s created" % obj)
            print(obj.type_id)
            obj.save()

        old_purposes = set([purp.pk for purp in obj.purposes.all()])
        new_purposes = set([purp.pk for purp in data['purposes']])
        if old_purposes != new_purposes:
            obj.purposes = new_purposes
            obj._changed_fields.append('purposes')

        if obj._changed:
            if not obj._created:
                print("%s changed: %s" % (obj, ', '.join(obj._changed_fields)))
            obj.save()

        return obj

    def __init__(self, options):
        self.logger = logging.getLogger("%s_importer" % self.name)

        if hasattr(settings, 'PROJECT_ROOT'):
            root_dir = settings.PROJECT_ROOT
        else:
            root_dir = settings.BASE_DIR
        self.data_paths = [os.path.join(root_dir, 'data')]
        module_path = os.path.dirname(__file__)
        app_path = os.path.abspath(os.path.join(module_path, '..', 'data'))
        self.data_paths.append(app_path)

        self.options = options

importers = {}


def register_importer(klass):
    importers[klass.name] = klass
    return klass


def get_importers():
    if importers:
        return importers
    module_path = __name__.rpartition('.')[0]
    # Importing the packages will cause their register_importer() methods
    # being called.
    for fname in os.listdir(os.path.dirname(__file__)):
        module, ext = os.path.splitext(fname)
        if ext.lower() != '.py':
            continue
        if module in ('__init__', 'base'):
            continue
        full_path = "%s.%s" % (module_path, module)
        ret = __import__(full_path, locals(), globals())
    return importers
