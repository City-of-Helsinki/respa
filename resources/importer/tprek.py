"""
munigeo importer for Finnish nation-level data
"""

import dateutil.parser
import requests
from django.contrib.gis.geos import Point

from ..models import Unit
from .base import Importer, register_importer
from .sync import ModelSyncher


def generate_tprek_id(obj):
    return obj.identifiers.get(namespace='tprek').value


@register_importer
class TPRekImporter(Importer):
    name = "tprek"

    def _import_unit(self, data, syncher):
        tprek_id = str(data['id'])

        data['id'] = 'tprek:' + tprek_id

        ids = data.setdefault('identifiers', [])
        for id_data in ids:
            if id_data.get('namespace') == 'tprek':
                break
        else:
            id_data = {'namespace': 'tprek'}
            ids.append(id_data)
        id_data['value'] = tprek_id

        location = data.get('location')
        if location is not None:
            assert location['type'] == 'Point'
            coords = location['coordinates']
            point = Point(x=coords[0], y=coords[1], srid=4326)
            data['location'] = point

        data['modified_at'] = dateutil.parser.parse(data['last_modified_time'])
        data['www_url'] = data['www']
        data['address_postal_full'] = None  # field does not support translation in respa

        obj = syncher.get(tprek_id)
        saved_obj = self.save_unit(data, obj)
        if obj:
            syncher.mark(obj)
        else:
            syncher.mark(saved_obj)

    def import_units(self, url=None):
        print("Fetching units")
        # 813 == Public libraries
        # 468 == Youth centers
        if not url:
            url = "https://api.hel.fi/servicemap/v2/unit/?service=813,468&municipality=helsinki&include=department&page_size=1000"
        resp = requests.get(url)
        assert resp.status_code == 200
        data = resp.json()

        unit_list = Unit.objects.filter(identifiers__namespace='tprek').distinct()
        syncher = ModelSyncher(unit_list, generate_tprek_id)

        if 'results' in data:
            units = data['results']
        else:
            units = [data]

        for unit_data in units:
            self._import_unit(unit_data, syncher)

        # Comment this out, because otherwise syncher would delete a lot of units...
        # syncher.finish()
