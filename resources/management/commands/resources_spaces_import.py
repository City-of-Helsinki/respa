import csv
import enum
import os

from django.core.management import BaseCommand, CommandError
from django.utils import translation

from resources.models import Resource, Unit, ResourceType, Purpose, ResourceGroup


class Columns(enum.Enum):
    is_public = 0
    unit = 1
    recourse_type = 2
    purpose = 3
    name = 4
    description = 5
    authentication_type = 6
    people_capacity = 7
    area = 8
    min_period = 9
    max_period = 10
    is_reservable = 11
    reservation_info = 12
    resource_group = 13


class Command(BaseCommand):
    help = "Import resources via csv file. This is for importing resources for spaces"

    def add_arguments(self, parser):
        parser.add_argument(
            "file_path", help="Path to the csv file",
        )

    @staticmethod
    def get_authentication_type(authentication_type_fi):
        if authentication_type_fi == "ei mitään":
            return "none"
        with translation.override("fi"):
            authentication_type = dict(Resource.AUTHENTICATION_TYPES)
            name = [k for k in authentication_type.keys() if
                    authentication_type[k] == authentication_type_fi]
            return name[0]

    def handle(self, *args, **options):
        file_path = options["file_path"]
        if not os.path.exists(file_path):
            raise CommandError("File {0} does not exist".format(file_path))

        with open(file_path) as f:
            csv_reader = csv.reader(f, delimiter=";")
            print("Processing...")
            for idx, row in enumerate(csv_reader):
                if idx == 0 or not row[Columns.name.value]:
                    continue
                resource = Resource()
                resource.public = True if row[Columns.is_public.value] else False
                unit = Unit.objects.filter(street_address__iexact=row[Columns.unit.value])
                if not unit:
                    unit = Unit(name=row[Columns.unit.value].split(",")[0], street_address=row[Columns.unit.value])
                    unit.save()
                else:
                    unit = unit[0]
                resource.unit = unit
                resource_type = ResourceType.objects.filter(name__iexact=row[Columns.recourse_type.value])
                if not resource_type:
                    resource_type = ResourceType(name=row[Columns.recourse_type.value], main_type="space")
                    resource_type.save()
                else:
                    resource_type = resource_type[0]
                resource.type = resource_type
                resource.name = row[Columns.name.value]
                resource.description = row[Columns.description.value]
                resource.authentication = self.get_authentication_type(row[Columns.authentication_type.value])
                resource.people_capacity = None if row[Columns.people_capacity.value] == "" else row[Columns.people_capacity.value]
                resource.area = None if row[Columns.area.value] == "" else row[Columns.area.value]
                if not row[Columns.min_period.value] == "":
                    resource.min_period = row[Columns.min_period.value]
                if not row[Columns.max_period.value] == "":
                    resource.max_period = row[Columns.max_period.value]
                resource.reservable = True if row[Columns.is_reservable.value] else False
                resource.reservation_info = row[Columns.reservation_info.value]
                resource.save()
                purpose = Purpose.objects.filter(name__iexact=row[Columns.purpose.value])
                if not purpose:
                    purpose = Purpose.objects.create(name=row[Columns.purpose.value])
                else:
                    purpose = purpose[0]
                resource.purposes.add(purpose)

                resource_group = ResourceGroup.objects.filter(name__iexact=row[Columns.resource_group.value])
                if not resource_group:
                    resource_group = ResourceGroup.objects.create(name=row[Columns.resource_group.value])
                    resource_group.resources.add(resource)
                else:
                    resource_group[0].resources.add(resource)
            print("Done!")
