import logging
import sys

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


def configure_console_log(logger="respa_exchange", level=logging.INFO):
    logger = logging.getLogger(logger)
    logger.setLevel(level)
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s: %(message)s",
        datefmt=logging.Formatter.default_time_format
    ))
    logger.addHandler(handler)
