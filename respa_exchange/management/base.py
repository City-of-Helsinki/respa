import logging
import sys

from django.core.management import CommandError
from django.conf import settings

from respa_exchange.models import ExchangeResource

rx_logger = logging.getLogger("respa_exchange")


def get_active_download_resources(exchange_configs):
    """
    Get resources that are enabled for downward (to-Respa) sync.

    :param exchange_configs: Exchange configurations to look at. These will be assigned to the respective resources.
    :type exchange_configs: list[respa_exchange.models.ExchangeConfiguration]
    :rtype: list[respa_exchange.models.ExchangeResource]
    """
    resources = []
    for exchange in exchange_configs:
        for ex_resource in ExchangeResource.objects.filter(
            sync_to_respa=True,
            exchange=exchange,
            exchange__enabled=True
        ):
            ex_resource.exchange = exchange  # Allow sharing the EWS session
            resources.append(ex_resource)
    return resources


def configure_logging(logger="respa_exchange", level=logging.INFO, handler=None):
    logger = logging.getLogger(logger)
    logger.setLevel(level)
    if not handler:
        handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s: %(message)s",
        datefmt=logging.Formatter.default_time_format
    ))
    logger.addHandler(handler)
    if hasattr(settings, 'RAVEN_CONFIG') and 'dsn' in settings.RAVEN_CONFIG:
        from raven.handlers.logging import SentryHandler
        from raven.conf import setup_logging

        sentry_handler = SentryHandler(settings.RAVEN_CONFIG['dsn'])
        sentry_handler.setLevel(logging.ERROR)
        logger.addHandler(sentry_handler)
        setup_logging(sentry_handler)


def select_resources(resources, selected_resources):
    ret = []
    for res_id in selected_resources:
        for res in resources:
            try:
                if int(res_id) == res.id:
                    break
            except ValueError:
                pass
            if res_id == res.principal_email:
                break
        else:
            raise CommandError('Resource with ID "%s" not found' % res_id)
        ret.append(res)
    return ret
