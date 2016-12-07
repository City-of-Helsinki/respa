class CommonExcludeMixin(object):
    readonly_fields = ('id',)
    exclude = ('created_at', 'created_by', 'modified_at', 'modified_by')


class PopulateCreatedAndModifiedMixin(object):
    def save_model(self, request, obj, form, change):
        if change is False:
            obj.created_by = request.user
        obj.modified_by = request.user
        obj.save()


class ExtraReadonlyFieldsOnUpdateMixin(object):
    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        field_names = getattr(self, 'extra_readonly_fields_on_update', [])

        if obj:
            readonly_fields.extend(field_names)

        return tuple(readonly_fields)
