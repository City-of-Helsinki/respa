from respa import VERSION
from rest_framework.renderers import BrowsableAPIRenderer


class ResourcesBrowsableAPIRenderer(BrowsableAPIRenderer):
    ''' Override DRF's BrowsableAPIRenderer to append data to context '''
    def get_context(self, data, accepted_media_type, renderer_context):
        context = super().get_context(data, accepted_media_type, renderer_context)
        context['RESPA_VERSION'] = f'v{VERSION}'
        return context
