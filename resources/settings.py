from django.conf import settings

RESOURCE_SERIALIZER_CLASS = getattr(settings, 'RESPA_RESOURCES_RESOURCE_SERIALIZER_CLASS', 'resources.api.resource.ResourceSerializer')
RESOURCE_DETAILS_SERIALIZER_CLASS = getattr(settings, 'RESPA_RESOURCES_RESOURCE_DETAILS_SERIALIZER_CLASS', 'resources.api.resource.ResourceDetailsSerializer')