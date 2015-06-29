"""
munigeo importer for Finnish nation-level data
"""

import os
import requests

from django import db
from django.contrib.gis.gdal import DataSource, SpatialReference, CoordTransform
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Polygon, Point

from .base import Importer, register_importer
from .sync import ModelSyncher
from ..models import Unit


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


        data['modified_at'] = data['origin_last_modified_time']

        obj = syncher.get(tprek_id)
        saved_obj = self.save_unit(data, obj)
        if not obj:
            syncher.mark(saved_obj)


    def import_units(self):
        print("Fetching units")
        # 25480 == Public libraries
        url = "http://api.hel.fi/servicemap/v1/unit/?service=25480&page_size=1000"
        resp = requests.get(url)
        assert resp.status_code == 200
        data = resp.json()

        unit_list = Unit.objects.filter(identifiers__namespace='tprek').distinct()
        syncher = ModelSyncher(unit_list, generate_tprek_id)

        for unit_data in data['results']:
            self._import_unit(unit_data, syncher)

        syncher.finish()
