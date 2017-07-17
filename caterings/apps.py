from django.apps import AppConfig


class CateringsConfig(AppConfig):
    name = 'caterings'

    def ready(self):
        import caterings.signal_handlers  # noqa
