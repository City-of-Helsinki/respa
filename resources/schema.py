from graphene import Field, List, ObjectType, Schema, String


class Purpose(ObjectType):
    name = String()


class AvailableResources(ObjectType):
    id = String()
    name = String()


class AvailableServices(ObjectType):
    id = String()
    name = String()


class Address(ObjectType):
    street = String()
    zip_code = String(name='zip')
    city = String()


class Space(ObjectType):
    id = String()
    name = String()
    address = Field(Address)

    # These are not actually needed in this case.
    # Graphene default resolver returns an attribute or dictionary key
    # with the same name as the field
    # https://docs.graphene-python.org/en/latest/types/objecttypes/#defaultresolver
    def resolve_id(parent, info):
        return parent['id']

    def resolve_name(parent, info):
        return parent['name']


class ReservationUnit(ObjectType):
    id = String()
    name = String()
    space = Field(Space)
    available_resources = Field(AvailableResources)
    available_services = Field(AvailableServices)
    purpose = Field(AvailableResources)

    def resolve_id(parent, info):
        return parent['id']

    def resolve_name(parent, info):
        return parent['name']

    def resolve_space(parent, info):
        return parent['space']


class Query(ObjectType):
    reservation_unit = Field(ReservationUnit)
    reservation_units = List(ReservationUnit, purpose=String())

    def resolve_reservation_units(parent, info, **kwargs):
        all_units = [
            {
                "id": "4",
                "name": "Esimerkki",
                "purpose": {
                    "name": "events"
                },
                "space": {
                    "id": "5",
                    "name": "Tilan nimi",
                    "address": {
                        "street": "Sammonkatu 23",
                        "zip_code": "33540",
                        "city": "Tampere",
                    },
                },
                "available_resources": {
                    "id": 1,
                    "name": "Kitara"
                },
                "available_services": {
                    "id": 8,
                    "name": "Catering palvelu"
                }
            },
            {
                "id": "4",
                "name": "Toinen esimerkki",
                "purpose": {
                    "name": "something-else"
                },
                "space": {
                    "id": "5",
                    "name": "Toisen tilan nimi",
                    "address": {
                        "street": "Sammonkatu 13",
                        "zip_code": "33540",
                        "city": "Tampere",
                    },
                },
                "available_resources": {
                    "id": 1,
                    "name": "Kitara"
                },
                "available_services": {
                    "id": 8,
                    "name": "Catering palvelu"
                }
            },
        ]

        if 'purpose' in kwargs:
            return [unit for unit in all_units if kwargs['purpose'] in unit['purpose']['name']]

        return all_units


schema = Schema(
    query=Query,
)
