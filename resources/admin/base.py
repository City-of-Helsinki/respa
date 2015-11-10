class CommonExcludeMixin(object):
    readonly_fields = ('id',)
    exclude = ('created_at', 'created_by', 'modified_at', 'modified_by')
