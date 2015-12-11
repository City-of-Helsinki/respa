class CommonExcludeMixin(object):
    readonly_fields = ('id',)
    exclude = ('created_at', 'created_by', 'modified_at', 'modified_by')


class PopulateCreatedAndModifiedMixin(object):
    def save_model(self, request, obj, form, change):
        if change is False:
            obj.created_by = request.user
        obj.modified_by = request.user
        obj.save()
