from django.db.models import Index

# Backported from Django 2.0


class MaxLengthMixin:
    # Allow an index name longer than 30 characters since the suffix is 4
    # characters (usual limit is 3). Since this index can only be used on
    # PostgreSQL, the 30 character limit for cross-database compatibility isn't
    # applicable.
    max_name_length = 31


class GistIndex(MaxLengthMixin, Index):
    suffix = 'gist'

    def __init__(self, *, buffering=None, fillfactor=None, **kwargs):
        self.buffering = buffering
        self.fillfactor = fillfactor
        super().__init__(**kwargs)

    def deconstruct(self):
        path, args, kwargs = super().deconstruct()
        if self.buffering is not None:
            kwargs['buffering'] = self.buffering
        if self.fillfactor is not None:
            kwargs['fillfactor'] = self.fillfactor
        return path, args, kwargs

    def create_sql(self, model, schema_editor):
        statement = super().create_sql(model, schema_editor, using=' USING gist')
        with_params = []
        if self.buffering is not None:
            with_params.append('buffering = {}'.format('on' if self.buffering else 'off'))
        if self.fillfactor is not None:
            with_params.append('fillfactor = %s' % self.fillfactor)
        if with_params:
            statement.parts['extra'] = 'WITH ({}) {}'.format(', '.join(with_params), statement.parts['extra'])
        return statement
