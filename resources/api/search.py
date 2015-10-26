from django.db.models import Q
from django.utils.encoding import force_text
from rest_framework import viewsets
from rest_framework.fields import BooleanField
from rest_framework.response import Response

from resources.api.resource import ResourceListViewSet
from resources.api.unit import UnitViewSet


class TypeaheadViewSet(viewsets.ViewSet):
    """
    Get typeahead suggestions for objects based on an arbitrary user
    input (the `input` query parameter).

    The format of the return data is a mapping of object type to a list
    of object representations.

    By default, just the object's `id` and a related `text`
    are returned. This can be changed with the `full` query parameter.
    If `full` is a truthy value, then the same representation is used as
    with the regular object endpoints.

    By default, all supported object types are returned, but this can
    be limited by the comma-separated `types` query parameter.

    Currently supported are "resource" and "unit".
    """
    objects = {
        "resource": {"search_fields": ["name"], "viewset": ResourceListViewSet, "text_getter": force_text},
        "unit": {"search_fields": ["name"], "viewset": UnitViewSet, "text_getter": force_text},
    }

    def list(self, request, *args, **kwargs):
        return Response(dict(self.get_object_lists(request)))

    def get_object_lists(self, request):
        query_parts = [
            part.lower()
            for part in request.query_params.get("input", "").split(None)
            if len(part) >= 2
            ]
        if not query_parts:
            return

        full = BooleanField().to_internal_value(request.query_params.get("full", "false"))
        requested_objects = set(request.query_params.get("types", ",".join(self.objects.keys())).split(","))

        for obj_name in requested_objects:
            obj_list = self.get_single_object_type_object_list(request, obj_name, query_parts, full=full)
            if obj_list:
                yield obj_list

    def get_single_object_type_object_list(self, request, obj_name, query_parts, full=False):
        # TODO: Could add caching here, keyed on `query_parts`
        obj_schema = self.objects.get(obj_name)
        if not obj_schema:
            return None
        q = self.build_q(obj_schema["search_fields"], query_parts)

        # Defer serialization and queryset retrieval to the viewsets that are in use
        # in the general API.
        viewset_class = obj_schema["viewset"]
        object_viewset = viewset_class(request=request)
        object_viewset.initial(request)
        queryset = object_viewset.get_queryset().filter(q)[:10]  # TODO: Sort these?
        if queryset.exists():
            if full:
                data = object_viewset.get_serializer(queryset, many=True).data
            else:
                text_getter = obj_schema["text_getter"]
                data = [{"id": obj.pk, "text": text_getter(obj)} for obj in queryset]
            return (obj_name, data)

    def build_q(self, fields, query_parts):
        q = Q()
        for field in fields:
            field_q = Q()
            for i, part in enumerate(query_parts):
                key = ("%s__istartswith" % field if i == 0 else "%s__icontains" % field)
                field_q &= Q(**{key: part})
            q |= field_q
        return q
