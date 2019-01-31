from django.apps import AppConfig

from .signal_handlers import install_signal_handlers


class KulkunenConfig(AppConfig):
    name = 'kulkunen'
    verbose_name = 'Kulkunen'

    def ready(self):
        install_signal_handlers()
