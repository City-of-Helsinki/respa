from django.http import HttpResponse, HttpResponseBadRequest
from xlsxwriter.workbook import Workbook
from modeltranslation.translator import translator, NotRegistered
from django.apps import apps
from resources.models.utils import make_translation_excel
from django.conf import settings


def export_translated_models(request):
    """
    Returns Excel of translated strings in given models

    Accepts as arguments either *all* which exports models from
    settings.TRANSLATED_MODELS_EXPORT
    or *models* as comma separated model name list

    :param request:Django HttpRequest
    :return:Django HttpResponse
    """

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = "attachment; filename=test.xlsx"

    if request.GET.get('all') and request.GET.get('models'):
        return HttpResponseBadRequest("Use only all or models, not both")

    if request.GET.get('all'):
        models = settings.TRANSLATED_MODELS_EXPORT
    elif request.GET.get('models'):
        models = request.GET.get('models').split(',')
    else:
        return HttpResponseBadRequest("Please give all or specific models")

    # Validate models
    for model_name in models:
        try:
            apps.get_model('resources', model_name)
        except Exception as e:
            return HttpResponseBadRequest(("Problem finding model '%s': " % model_name) + str(e))

    data = {}

    for model_name in models:
        model = apps.get_model('resources', model_name)
        trans_opts = translator.get_options_for_model(model)
        translated_fields = sorted([tr_field.name for field in trans_opts.fields.values() for tr_field in field])

        data[model_name] = [translated_fields, model.objects.all()]

    result = make_translation_excel(response, data)

    if not result:
        return HttpResponseBadRequest("Problem with producing Excel")

    return response
