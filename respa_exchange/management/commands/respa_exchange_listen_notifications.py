import os
import logging
import atexit
from contextlib import closing

from daemonize import Daemonize
from django.core.management import BaseCommand

from respa_exchange.listener import NotificationListener
from respa_exchange.management.base import configure_logging


logger = logging.getLogger('respa_exchange.notication_listener')


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--daemonize', action='store_true', help='daemonize the listener')
        parser.add_argument('--pid-file', metavar='FILE', help='store the PID in the given file')
        parser.add_argument('--log-file', metavar='FILE', help='write logs to the given file')

    def handle(self, verbosity, *args, **options):
        log_handler = None
        log_file = options.get('log_file')
        if log_file is not None:
            log_handler = logging.FileHandler(log_file)
        if verbosity >= 3:
            configure_logging(level=logging.DEBUG, handler=log_handler)
            configure_logging(level=logging.DEBUG, logger='ExchangeSession', handler=log_handler)
        elif verbosity >= 2 or log_handler is not None:
            configure_logging(handler=log_handler)

        pid_file = options.get('pid_file')
        if options['daemonize']:
            if not pid_file:
                self.stderr.write(self.style.ERROR("--daemonize requires also the --pid-file argument"))
                exit(1)
            kwargs = {}
            if log_handler:
                kwargs['keep_fds'] = [log_handler.stream.fileno()]

            listener = None

            def run_listener():
                atexit.register(stop_listener)
                listener = NotificationListener(sync_after_start=True)
                listener.start()

            def stop_listener():
                logger.info("Stopping listener")
                listener.close()

            daemon = Daemonize(app='respa_exchange_listen', pid=pid_file, action=run_listener,
                               logger=logger, **kwargs)
            daemon.start()
        else:
            pid_file = options.get('pid_file')
            if pid_file:
                pid = str(os.getpid())
                with open(pid_file, 'w') as f:
                    f.write(pid)
            with closing(NotificationListener()) as listener:
                listener.start()
