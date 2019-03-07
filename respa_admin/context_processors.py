from django.conf import settings


def export_global_vars(request):
    data = {}
    data['RESPA_ADMIN_INSTRUCTIONS_URL'] = settings.RESPA_ADMIN_INSTRUCTIONS_URL
    return data
