import json
import datetime
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from rest_framework import permissions, generics
from resources.models import Unit, Reservation, Resource, ResourceType
from hmlvaraus.models.hml_reservation import HMLReservation
from hmlvaraus.models.berth import Berth
from django.contrib.gis.geos import GEOSGeometry
from rest_framework import status
from rest_framework.response import Response

from django.utils.dateparse import parse_datetime
import pytz

class ImporterView(generics.CreateAPIView):
    base_name = 'importer'
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        request_user = request.user

        if not request_user.is_staff:
            raise PermissionDenied()

        uploaded_file = request.data['file']
        data = uploaded_file.read().decode("utf-8")

        data_rows = data.split('\n')

        # Kohteet
        if data_rows[0][0] == '1':
            del data_rows[1]
            del data_rows[0]
            for row in data_rows:
                fields = row.split(';')

                try:
                    print('Kohdedataa')
                    a = fields[5]
                except:
                    continue

                location = None
                if fields[5] and fields[5] != '':
                    location = fields[5].split(',')
                    coordinates = []
                    for coord in location:
                        coord = coord.strip()
                        coord = float(coord)
                        coordinates = [coord] + coordinates

                    location = GEOSGeometry(json.dumps({'type': 'Point', 'coordinates': coordinates}))
                Unit.objects.get_or_create(name=fields[0], street_address=fields[1], address_zip=fields[2], email=fields[3], phone=fields[4], location=location, description=fields[6])


        # Venepaikat
        if data_rows[0][0] == '2':
            del data_rows[1]
            del data_rows[0]
            for row in data_rows:
                fields = row.split(';')

                try:
                    print('Venepaikkadataa, Kohde:', fields[0])
                    unit = Unit.objects.get(name=fields[0]);
                except:
                    continue

                resource_types = ResourceType.objects.all();
                for resource_type in resource_types:
                    if 'vene' in resource_type.name.lower() or 'boat' in resource_type.name.lower():
                        type_instance = resource_type

                resource = Resource.objects.get_or_create(unit=unit, name=fields[1], description=fields[2], type=type_instance, reservable=True)[0]
                is_disabled = False
                if fields[3] == 'kyllä':
                    is_disabled = True
                price = 0
                if fields[4]:
                    price = fields[4].replace(',', '.')
                    price = float(price)

                type_mapping = {
                    'numero': 'number',
                    'laituri': 'dock',
                    'poletti': 'ground'
                }
                length = 0
                width = 0
                depth = 0
                if fields[5] and fields[5] != '':
                    length = int(fields[5])
                if fields[6] and fields[6] != '':
                    width = int(fields[6])
                if fields[7] and fields[7] != '':
                    depth = int(fields[7])

                berth_type = type_mapping.get(fields[8].lower(), None)
                Berth.objects.get_or_create(resource=resource, is_disabled=is_disabled, price=price, length_cm=length, width_cm=width, depth_cm=depth, type=berth_type)


        # Varaukset
        if data_rows[0][0] == '3':
            del data_rows[1]
            del data_rows[0]
            for i, row in enumerate(data_rows):
                fields = row.split(';')
                try:
                    print(i, 'Varausdataa, Kohde:', fields[1])
                    unit = Unit.objects.get(name=fields[1])
                    resource = Resource.objects.get(unit=unit, name=str(fields[0]), description=str(fields[4]))
                except:
                    continue

                resource.reservable = False

                berth = Berth.objects.get(resource=resource)
                begin = parse_datetime(str(fields[2]) + ' 00:00:00')
                begin = pytz.timezone("Europe/Helsinki").localize(begin, is_dst=None)
                end = parse_datetime(str(fields[3]) + ' 00:00:00')
                end = pytz.timezone("Europe/Helsinki").localize(end, is_dst=None)

                state = 'confirmed'
                state_updated_at = timezone.now()
                is_paid = False
                is_paid_at = None
                if fields[5] and fields[5].strip() != '':
                    state_updated_at = datetime.datetime.strptime(fields[5], "%d.%m.%Y %H:%M")
                    state = 'cancelled'

                if fields[6] and fields[6].strip() != '':
                    is_paid_at = datetime.datetime.strptime(fields[6], "%d.%m.%Y %H:%M")
                    is_paid = True


                reservation = Reservation.objects.create(
                    resource=resource,
                    begin=begin,
                    end=end,
                    event_description=fields[4] or '',
                    state=state,
                    reserver_name=fields[7] or '',
                    reserver_email_address=fields[8] or '',
                    reserver_phone_number=fields[9] or '',
                    reserver_address_street=fields[10] or '',
                    reserver_address_city=fields[11] or '',
                    reserver_address_zip=fields[12] or '',
                )

                HMLReservation.objects.get_or_create(reservation=reservation, berth=berth, state_updated_at=state_updated_at, is_paid_at=is_paid_at, is_paid=is_paid)
                resource.save()

        return Response(
            status=status.HTTP_201_CREATED
        )
