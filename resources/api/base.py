from django.conf import settings
from django.utils import timezone
import django_filters
from modeltranslation.translator import NotRegistered, translator
from rest_framework import serializers

all_views = []


def register_view(klass, name, base_name=None):
    entry = {'class': klass, 'name': name}
    if base_name is not None:
        entry['base_name'] = base_name
    all_views.append(entry)


LANGUAGES = [x[0] for x in settings.LANGUAGES]


class TranslatedModelSerializer(serializers.ModelSerializer):

    def __init__(self, *args, **kwargs):
        super(TranslatedModelSerializer, self).__init__(*args, **kwargs)
        model = self.Meta.model
        try:
            trans_opts = translator.get_options_for_model(model)
        except NotRegistered:
            self.translated_fields = []
            return

        self.translated_fields = trans_opts.fields.keys()
        # Remove the pre-existing data in the bundle.
        for field_name in self.translated_fields:
            for lang in LANGUAGES:
                key = "%s_%s" % (field_name, lang)
                if key in self.fields:
                    del self.fields[key]

    def to_representation(self, obj):
        ret = super(TranslatedModelSerializer, self).to_representation(obj)
        if obj is None:
            return ret

        for field_name in self.translated_fields:
            if field_name not in self.fields:
                continue
            d = {}
            for lang in LANGUAGES:
                key = "%s_%s" % (field_name, lang)
                val = getattr(obj, key, None)
                if val in (None, ""):
                    continue
                d[lang] = val

            # If no text provided, leave the field as null
            d = (d or None)
            ret[field_name] = d

        return ret


class NullableTimeField(serializers.TimeField):

    def to_representation(self, value):
        if not value:
            return None
        else:
            value = timezone.localtime(value)
        return super().to_representation(value)


class NullableDateTimeField(serializers.DateTimeField):

    def to_representation(self, value):
        if not value:
            return None
        else:
            value = timezone.localtime(value)
        return super().to_representation(value)


class DRFFilterBooleanWidget(django_filters.widgets.BooleanWidget):
    """
    Without this Django complains about missing render method when DRF renders HTML version of API.
    """
    def render(self, *args, **kwargs):
        return None
