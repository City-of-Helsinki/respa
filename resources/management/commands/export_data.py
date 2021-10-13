import logging
from functools import singledispatch
from json import dumps
from typing import NoReturn, Any, List, TypeVar, Optional

from django.contrib.contenttypes.models import ContentType
from django.contrib.gis.forms import GeometryField
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Model
from helusers.models import ADGroup, ADGroupMapping
from munigeo.models import Municipality, AdministrativeDivision, Building, Address, Street

from caterings.models import CateringProvider, CateringProductCategory, CateringProduct, CateringOrder, CateringOrderLine
from comments.models import Comment
from kulkunen.models import AccessControlUser, AccessControlSystem, AccessControlResource
from notifications.models import NotificationTemplate
from payments.models import Product, Order, OrderLine, OrderLogEntry, ReservationCustomPrice
from resources.models import Day, Period, Unit, UnitGroup, UnitGroupAuthorization, Equipment, EquipmentCategory, \
    EquipmentAlias, Purpose, Resource, TermsOfUse, ReservationMetadataSet, ReservationMetadataField, ResourceType, \
    Reservation
from resources.models.base import ModifiableModel
from users.models import User
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


logger = logging.getLogger(__name__)

T = TypeVar("T")


class Command(BaseCommand):
    help = 'Exports all Respa data to standard output in JSON format.'

    def handle(self, *args, **options) -> None:
        json_string = dumps(serialize_everything(), indent=2)
        self.stdout.write(json_string)


def _geometry(field: GeometryField) -> Optional[str]:
    return getattr(field, 'ewkt') if field is not None else None


def _parler_translations(obj: Model, field: str) -> dict:
    translations = {}
    for language_code in ["fi", "sv", "en"]:
        try:
            translations[language_code] = getattr(obj.get_translation(language_code), field)
        except ObjectDoesNotExist:
            translations[language_code] = None
    return translations


def _model_translations(obj: Model, field: str) -> dict:
    translations = {}
    for language_code in ["fi", "sv", "en"]:
        translations[language_code] = getattr(obj, f"{field}_{language_code}")
    return translations


def _pk_list(field: Any) -> List[int]:
    return list(field.values_list("pk", flat=True))


@singledispatch
def serialize(_: Any) -> NoReturn:
    raise NotImplementedError


@serialize.register(User)
def serialize_user(obj: User) -> dict:
    return {
        # AbstractBaseUser fields
        "password": obj.password,
        "last_login": obj.last_login.isoformat() if obj.last_login is not None else None,
        "is_active": obj.is_active,
        # PermissionsMixin fields
        "is_superuser": obj.is_superuser,
        "groups": _pk_list(obj.groups),
        "user_permissions": _pk_list(obj.user_permissions),
        # DjangoAbstractUser fields
        "username": obj.username,
        "first_name": obj.first_name,
        "last_name": obj.last_name,
        "email": obj.email,
        "is_staff": obj.is_staff,
        # This is already defined in AbstractBaseUser
        # "is_active": obj.is_active,
        "date_joined": obj.date_joined.isoformat() if obj.date_joined is not None else None,
        # AbstractUser fields
        "uuid": str(obj.uuid),
        "department_name": obj.department_name,
        "ad_groups": _pk_list(obj.ad_groups),
        # User fields
        "pk": obj.pk,
        "ical_token": obj.ical_token,
        "preferred_language": obj.preferred_language,
        "favorite_resources": _pk_list(obj.favorite_resources),
        # This is already defined in DjangoAbstractUser
        # "is_staff": obj.is_staff,
        "is_general_admin": obj.is_general_admin,
    }


@serialize.register(ContentType)
def serialize_content_type(obj: ContentType):
    return {
        "pk": obj.pk,
        "app_label": obj.app_label,
        "model": obj.model,
    }


@serialize.register(Permission)
def serialize_permission(obj: Permission):
    return {
        "pk": obj.pk,
        "name": obj.name,
        "content_type": obj.content_type_id,
        "codename": obj.codename,
    }


@serialize.register(Group)
def serialize_group(obj: Group) -> dict:
    return {
        "pk": obj.pk,
        "name": obj.name,
        "permissions": _pk_list(obj.permissions),
    }


@serialize.register(ADGroup)
def serialize_ad_group(obj: ADGroup) -> dict:
    return {
        "pk": obj.pk,
        "name": obj.name,
        "display_name": obj.display_name,
    }


@serialize.register(ADGroupMapping)
def serialize_ad_group_mapping(obj: ADGroupMapping) -> dict:
    return {
        "pk": obj.pk,
        "group": obj.group_id,
        "ad_group": obj.ad_group_id,
    }


@serialize.register(Day)
def serialize_day(obj: Day) -> dict:
    return {
        "pk": obj.pk,
        "period": obj.period_id,
        "weekday": obj.weekday,
        "opens": obj.opens.isoformat() if obj.opens is not None else None,
        "closes": obj.closes.isoformat() if obj.closes is not None else None,
        "length": {
            "lower": obj.length.lower,
            "upper": obj.length.upper,
        } if obj.length is not None else None,
        "closed": obj.closed,
        "description": obj.description,
    }


@serialize.register(Period)
def serialize_period(obj: Period) -> dict:
    return {
        "pk": obj.pk,
        "resource": obj.resource_id,
        "unit": obj.unit_id,
        "start": obj.start.isoformat() if obj.start is not None else None,
        "end": obj.end.isoformat() if obj.end is not None else None,
        "name": obj.name,
        "description": obj.description,
        "closed": obj.closed,
    }


@serialize.register(ModifiableModel)
def serialize_modifiable_model(obj: ModifiableModel) -> dict:
    return {
        "created_at": obj.created_at.isoformat() if obj.created_at is not None else None,
        "created_by": obj.created_by_id,
        "modified_at": obj.modified_at.isoformat() if obj.modified_at is not None else None,
        "modified_by": obj.modified_by_id,
    }


@serialize.register(Unit)
def serialize_unit(obj: Unit) -> dict:
    return {
        **serialize.dispatch(ModifiableModel)(obj),
        "pk": obj.pk,
        "name": _model_translations(obj, "name"),
        "description": _model_translations(obj, "description"),
        "location": _geometry(obj.location),
        "time_zone": obj.time_zone,
        "manager_email": obj.manager_email,
        "street_address": _model_translations(obj, "street_address"),
        "address_zip": obj.address_zip,
        "phone": obj.phone,
        "email": obj.email,
        "www_url": _model_translations(obj, "www_url"),
        "address_postal_full": obj.address_postal_full,
        "municipality": obj.municipality_id,
        "picture_url": obj.picture_url,
        "picture_caption": _model_translations(obj, "picture_caption"),
        "reservable_max_days_in_advance": obj.reservable_max_days_in_advance,
        "reservable_min_days_in_advance": obj.reservable_min_days_in_advance,
        "data_source": obj.data_source,
        "data_source_hours": obj.data_source_hours,
        "disallow_overlapping_reservations": obj.disallow_overlapping_reservations,
    }


@serialize.register(UnitGroup)
def serialize_unit_group(obj: UnitGroup) -> dict:
    return {
        "pk": obj.pk,
        "name": _model_translations(obj, "name"),
        "members": _pk_list(obj.members),
    }


@serialize.register(UnitGroupAuthorization)
def serialize_unit_group_authorization(obj: UnitGroupAuthorization) -> dict:
    return {
        "pk": obj.pk,
        "subject": obj.subject_id,
        "level": obj.level.name,
        "authorized": obj.authorized_id,
    }


@serialize.register(Equipment)
def serialize_equipment(obj: Equipment) -> dict:
    return {
        **serialize.dispatch(ModifiableModel)(obj),
        "pk": obj.pk,
        "name": _model_translations(obj, "name"),
        "category": obj.category_id,
    }


@serialize.register(EquipmentCategory)
def serialize_equipment_category(obj: EquipmentCategory) -> dict:
    return {
        **serialize.dispatch(ModifiableModel)(obj),
        "pk": obj.pk,
        "name": _model_translations(obj, "name"),
    }


@serialize.register(EquipmentAlias)
def serialize_equipment_alias(obj: EquipmentAlias) -> dict:
    return {
        **serialize.dispatch(ModifiableModel)(obj),
        "pk": obj.pk,
        "name": obj.name,
        "language": obj.language,
        "equipment": obj.equipment_id,
    }


@serialize.register(Purpose)
def serialize_purpose(obj: Purpose) -> dict:
    return {
        **serialize.dispatch(ModifiableModel)(obj),
        "pk": obj.pk,
        "parent": obj.parent_id,
        "name": _model_translations(obj, "name"),
        "public": obj.public,
    }


@serialize.register(ResourceType)
def serialize_resource_type(obj: ResourceType) -> dict:
    return {
        **serialize.dispatch(ModifiableModel)(obj),
        "pk": obj.pk,
        "main_type": obj.main_type,
        "name": _model_translations(obj, "name"),
    }


@serialize.register(Resource)
def serialize_resource(obj: Resource) -> dict:
    return {
        **serialize.dispatch(ModifiableModel)(obj),
        "pk": obj.pk,
        "public": obj.public,
        "unit": obj.unit_id,
        "type": obj.type_id,
        "purposes": _pk_list(obj.purposes),
        "name": _model_translations(obj, "name"),
        "description": _model_translations(obj, "description"),
        "need_manual_confirmation": obj.need_manual_confirmation,
        "authentication": obj.authentication,
        "people_capacity": obj.people_capacity,
        "area": obj.area,
        "location": _geometry(obj.location),
        "min_period": obj.min_period.seconds if obj.min_period is not None else None,
        "max_period": obj.max_period.seconds if obj.max_period is not None else None,
        "slot_size": obj.slot_size.seconds if obj.slot_size is not None else None,
        "equipment": _pk_list(obj.equipment),
        "max_reservations_per_user": obj.max_reservations_per_user,
        "reservable": obj.reservable,
        "reservation_info": _model_translations(obj, "reservation_info"),
        "responsible_contact_info": _model_translations(obj, "responsible_contact_info"),
        "generic_terms": obj.generic_terms_id,
        "payment_terms": obj.payment_terms_id,
        "specific_terms": _model_translations(obj, "specific_terms"),
        "reservation_requested_notification_extra": _model_translations(obj, "reservation_requested_notification_extra"),
        "reservation_confirmed_notification_extra": _model_translations(obj, "reservation_confirmed_notification_extra"),
        "min_price": str(obj.min_price),  # Decimal
        "max_price": str(obj.max_price),  # Decimal
        "price_type": obj.price_type,
        "access_code_type": obj.access_code_type,
        "generate_access_codes": obj.generate_access_codes,
        "reservable_max_days_in_advance": obj.reservable_max_days_in_advance,
        "reservable_min_days_in_advance": obj.reservable_min_days_in_advance,
        "reservation_metadata_set": obj.reservation_metadata_set_id,
        "external_reservation_url": obj.external_reservation_url,
        "reservation_extra_questions": obj.reservation_extra_questions,
        "attachments": _pk_list(obj.attachments),
    }


@serialize.register(ReservationMetadataField)
def serialize_reservation_metadata_field(obj: ReservationMetadataField) -> dict:
    return {
        "pk": obj.pk,
        "name": obj.field_name,
    }


@serialize.register(ReservationMetadataSet)
def serialize_reservation_metadata_set(obj: ReservationMetadataSet) -> dict:
    return {
        **serialize.dispatch(ModifiableModel)(obj),
        "pk": obj.pk,
        "supported_fields": _pk_list(obj.supported_fields),
        "required_fields": _pk_list(obj.required_fields),
    }


@serialize.register(Reservation)
def serialize_reservation(obj: Reservation) -> dict:
    return {
        **serialize.dispatch(ModifiableModel)(obj),
        "pk": obj.pk,
        "resource": obj.resource_id,
        "begin": obj.begin.isoformat() if obj.begin is not None else None,
        "end": obj.end.isoformat() if obj.end is not None else None,
        "duration": {
            "lower": obj.duration.lower.isoformat() if obj.duration.lower is not None else None,
            "upper": obj.duration.upper.isoformat() if obj.duration.upper is not None else None,
            "bounds": obj.duration._bounds,
        } if obj.duration is not None else None,
        "comments": obj.comments,
        "user": obj.user_id,
        "state": obj.state,
        "approver": obj.approver_id,
        "staff_event": obj.staff_event,
        "access_code": obj.access_code,
        "event_subject": obj.event_subject,
        "event_description": obj.event_description,
        "number_of_participants": obj.number_of_participants,
        "participants": obj.participants,
        "host_name": obj.host_name,
        "reservation_extra_questions": obj.reservation_extra_questions,
        "reserver_name": obj.reserver_name,
        "reserver_id": obj.reserver_id,
        "reserver_email_address": obj.reserver_email_address,
        "reserver_phone_number": obj.reserver_phone_number,
        "reserver_address_street": obj.reserver_address_street,
        "reserver_address_zip": obj.reserver_address_zip,
        "reserver_address_city": obj.reserver_address_city,
        "company": obj.company,
        "billing_first_name": obj.billing_first_name,
        "billing_last_name": obj.billing_last_name,
        "billing_email_address": obj.billing_email_address,
        "billing_phone_number": obj.billing_phone_number,
        "billing_address_street": obj.billing_address_street,
        "billing_address_zip": obj.billing_address_zip,
        "billing_address_city": obj.billing_address_city,
        "origin_id": obj.origin_id,
    }


@serialize.register(TermsOfUse)
def serialize_terms_of_use(obj: TermsOfUse) -> dict:
    return {
        **serialize.dispatch(ModifiableModel)(obj),
        "pk": obj.pk,
        "name": _model_translations(obj, "name"),
        "text": _model_translations(obj, "text"),
        "terms_type": obj.terms_type,
    }


@serialize.register(Product)
def serialize_product(obj: Product) -> dict:
    return {
        "pk": obj.pk,
        "created_at": obj.created_at.isoformat() if obj.created_at is not None else None,
        "product_id": obj.product_id,
        "archived_at": obj.archived_at.isoformat() if obj.archived_at is not None else None,
        "type": obj.type,
        "sku": obj.sku,
        "name": obj.name,
        "description": obj.description,
        "price": str(obj.price),
        "tax_percentage": str(obj.tax_percentage),
        "price_type": obj.price_type,
        "price_period": obj.price_period.seconds if obj.price_period is not None else None,
        "max_quantity": obj.max_quantity,
        "resources": _pk_list(obj.resources),
    }


@serialize.register(Order)
def serialize_order(obj: Order) -> dict:
    return {
        "pk": obj.pk,
        "state": obj.state,
        "order_number": obj.order_number,
        "reservation": obj.reservation_id,
        "payment_url": obj.payment_url,
        "is_requested_order": obj.is_requested_order,
        "confirmed_by_staff_at": obj.confirmed_by_staff_at.isoformat() if obj.confirmed_by_staff_at is not None else None,
    }


@serialize.register(OrderLine)
def serialize_order_line(obj: OrderLine) -> dict:
    return {
        "pk": obj.pk,
        "order": obj.order_id,
        "product": obj.product_id,
        "quantity": obj.quantity,
    }


@serialize.register(OrderLogEntry)
def serialize_order_log_entry(obj: OrderLogEntry) -> dict:
    return {
        "pk": obj.pk,
        "order": obj.order_id,
        "timestamp": obj.timestamp.isoformat() if obj.timestamp is not None else None,
        "state_change": obj.state_change,
        "message": obj.message,
    }


@serialize.register(ReservationCustomPrice)
def export_reservation_custom_price(obj: ReservationCustomPrice) -> dict:
    return {
        "pk": obj.pk,
        "reservation": obj.reservation_id,
        "price": str(obj.price),
        "price_type": obj.price_type,
    }


@serialize.register(Municipality)
def serialize_municipality(obj: Municipality) -> dict:
    return {
        "pk": obj.pk,
        "division": obj.division_id,
        "translations": {
            "name": _parler_translations(obj, "name"),
        },
    }


@serialize.register(Street)
def serialize_street(obj: Street) -> dict:
    return {
        "pk": obj.pk,
        "municipality": obj.municipality_id,
        "modified_at": obj.modified_at.isoformat() if obj.modified_at is not None else None,
        "translations": {
            "name": _parler_translations(obj, "name"),
        }
    }


@serialize.register(Address)
def serialize_address(obj: Address) -> dict:
    return {
        "pk": obj.pk,
        "street": obj.street_id,
        "number": obj.number,
        "number_end": obj.number_end,
        "letter": obj.letter,
        "location": _geometry(obj.location),
        "modified_at": obj.modified_at.isoformat() if obj.modified_at is not None else None,
    }


@serialize.register(Building)
def serialize_building(obj: Building) -> dict:
    return {
        "pk": obj.pk,
        "origin_id": obj.origin_id,
        "municipality": obj.municipality_id,
        "geometry": _geometry(obj.geometry),
        "addresses": _pk_list(obj.addresses),
        "modified_at": obj.modified_at.isoformat() if obj.modified_at is not None else None,
    }


@serialize.register(AdministrativeDivision)
def serialize_division(obj: AdministrativeDivision) -> dict:
    return {
        "pk": obj.pk,
        "type": obj.type_id,
        "parent": obj.parent_id,
        "origin_id": obj.origin_id,
        "ocd_id": obj.ocd_id,
        "municipality": obj.municipality_id,
        "service_point_id": obj.service_point_id,
        "start": obj.start.isoformat() if obj.start is not None else None,
        "end": obj.end.isoformat() if obj.end is not None else None,
        "modified_at": obj.modified_at.isoformat() if obj.modified_at is not None else None,
        "translations": {
            "name": _parler_translations(obj, "name"),
        },
    }


@serialize.register(AccessControlSystem)
def serialize_access_control_system(obj: AccessControlSystem) -> dict:
    return {
        "pk": obj.pk,
        "name": obj.name,
        "driver": obj.driver,
        "reservation_leeway": obj.reservation_leeway,
        "driver_config": str(obj.driver_config) if obj.driver_config is not None else None,
        "driver_data": str(obj.driver_data) if obj.driver_data is not None else None,
    }


@serialize.register(AccessControlUser)
def serialize_access_control_user(obj: AccessControlUser) -> dict:
    return {
        "pk": obj.pk,
        "system": obj.system_id,
        "user": obj.user_id,
        "state": obj.state,
        "first_name": obj.first_name,
        "last_name": obj.last_name,
        "created_at": obj.created_at.isoformat() if obj.created_at is not None else None,
        "removed_at": obj.removed_at.isoformat() if obj.removed_at is not None else None,
        "identifier": obj.identifier,
        "driver_data": str(obj.driver_data) if obj.driver_data is not None else None,
    }


@serialize.register(AccessControlResource)
def serialize_access_control_resource(obj: AccessControlResource) -> dict:
    return {
        "pk": obj.pk,
        "system": obj.system_id,
        "resource": obj.resource_id,
        "identifier": obj.identifier,
        "driver_config": str(obj.driver_config) if obj.driver_config is not None else None,
        "driver_data": str(obj.driver_data) if obj.driver_data is not None else None,
    }


@serialize.register(CateringProvider)
def serialize_catering_provider(obj: CateringProvider) -> dict:
    return {
        "created_at": obj.created_at.isoformat() if obj.created_at is not None else None,
        "modified_at": obj.modified_at.isoformat() if obj.modified_at is not None else None,
        "pk": obj.pk,
        "name": obj.name,
        "price_list_url": obj.price_list_url,
        "units": _pk_list(obj.units),
        "notification_email": obj.notification_email,
    }


@serialize.register(CateringProductCategory)
def serialize_catering_product_category(obj: CateringProductCategory) -> dict:
    return {
        "created_at": obj.created_at.isoformat() if obj.created_at is not None else None,
        "modified_at": obj.modified_at.isoformat() if obj.modified_at is not None else None,
        "pk": obj.pk,
        "name": obj.name,
        "provider": obj.provider_id,
    }


@serialize.register(CateringProduct)
def serialize_catering_product(obj: CateringProduct) -> dict:
    return {
        "created_at": obj.created_at.isoformat() if obj.created_at is not None else None,
        "modified_at": obj.modified_at.isoformat() if obj.modified_at is not None else None,
        "pk": obj.pk,
        "name": obj.name,
        "category": obj.category_id,
        "description": obj.description,
    }


@serialize.register(CateringOrder)
def serialize_catering_order(obj: CateringOrder) -> dict:
    return {
        "created_at": obj.created_at.isoformat() if obj.created_at is not None else None,
        "modified_at": obj.modified_at.isoformat() if obj.modified_at is not None else None,
        "pk": obj.pk,
        "provider": obj.provider_id,
        "reservation": obj.reservation_id,
        "invoicing_data": obj.invoicing_data,
        "message": obj.message,
        "serving_time": obj.serving_time.isoformat() if obj.serving_time is not None else None,
    }


@serialize.register(CateringOrderLine)
def serialize_catering_order_line(obj: CateringOrderLine) -> dict:
    return {
        "pk": obj.pk,
        "product": obj.product_id,
        "quantity": obj.quantity,
        "order": obj.order_id,
    }


@serialize.register(Comment)
def serialize_comment(obj: Comment) -> dict:
    return {
        "pk": obj.pk,
        "created_at": obj.created_at.isoformat() if obj.created_at is not None else None,
        "created_by": obj.created_by_id,
        "text": obj.text,
        "content_type": obj.content_type_id,
        "object_id": obj.object_id,
    }


@serialize.register(NotificationTemplate)
def serialize_notification_template(obj: NotificationTemplate) -> dict:
    return {
        "pk": obj.pk,
        "type": obj.type,
        "translations": {
            "short_message": _parler_translations(obj, "short_message"),
            "subject": _parler_translations(obj, "subject"),
            "body": _parler_translations(obj, "body"),
            "html_body": _parler_translations(obj, "html_body"),
        }
    }


def serialize_all(model: T) -> List[T]:
    serialized_all = []
    for obj in model.objects.iterator():
        initial_serialized_obj = serialize(obj)
        serialized_obj = {}
        for field, value in initial_serialized_obj.items():
            if isinstance(value, dict):
                if field == "translations":
                    for translated_field, translated_value in value.items():
                        for suffix, inner_value in translated_value.items():
                            serialized_obj[f"{translated_field}_{suffix}"] = inner_value
                else:
                    for suffix, inner_value in value.items():
                        serialized_obj[f"{field}_{suffix}"] = inner_value
            else:
                serialized_obj[field] = value
        serialized_all.append(serialized_obj)
    return serialized_all


def serialize_everything() -> dict:
    return {
        # Django content types, permissions, groups
        "content_types": serialize_all(ContentType),
        "permissions": serialize_all(Permission),
        "groups": serialize_all(Group),
        # HelUsers
        "users": serialize_all(User),
        "ad_groups": serialize_all(ADGroup),
        "ad_group_mappings": serialize_all(ADGroupMapping),
        # Resources
        "days": serialize_all(Day),
        "periods": serialize_all(Period),
        "unit_groups": serialize_all(UnitGroup),
        "unit_group_authorizations": serialize_all(UnitGroupAuthorization),
        "units": serialize_all(Unit),
        "equipment_categories": serialize_all(EquipmentCategory),
        "equipment": serialize_all(Equipment),
        "equipment_aliases": serialize_all(EquipmentAlias),
        "purposes": serialize_all(Purpose),
        "resource_types": serialize_all(ResourceType),
        "resources": serialize_all(Resource),
        "terms_of_use": serialize_all(TermsOfUse),
        "reservation_metadata_fields": serialize_all(ReservationMetadataField),
        "reservation_metadata_sets": serialize_all(ReservationMetadataSet),
        "reservations": serialize_all(Reservation),
        # Kulkunen
        "access_control_systems": serialize_all(AccessControlSystem),
        "access_control_user": serialize_all(AccessControlUser),
        "access_control_resources": serialize_all(AccessControlResource),
        # Payments
        "products": serialize_all(Product),
        "orders": serialize_all(Order),
        "order_lines": serialize_all(OrderLine),
        "order_log_entries": serialize_all(OrderLogEntry),
        "reservation_custom_prices": serialize_all(ReservationCustomPrice),
        # Caterings
        "catering_providers": serialize_all(CateringProvider),
        "catering_product_categories": serialize_all(CateringProductCategory),
        "catering_products": serialize_all(CateringProduct),
        "catering_orders": serialize_all(CateringOrder),
        "catering_order_lines": serialize_all(CateringOrderLine),
        # Comments
        "comments": serialize_all(Comment),
        # Notifications
        "notification_templates": serialize_all(NotificationTemplate),
        # MuniGeo
        "municipalities": serialize_all(Municipality),
        "street": serialize_all(Street),
        "address": serialize_all(Address),
        "buildings": serialize_all(Building),
        "divisions": serialize_all(AdministrativeDivision),
    }
