from django.conf import settings
from django.utils.module_loading import import_string


def get_ews_session():
    """
    Get a configured EWS session.

    :rtype:   respa_exchange.ews.session.ExchangeSession
    """
    # TODO: Maybe cache or something? NTLM handshakes can take some time...
    session_class = import_string(
        getattr(settings, "RESPA_EXCHANGE_EWS_SESSION_CLASS", "respa_exchange.ews.session.ExchangeSession")
    )
    return session_class(
        url=settings.RESPA_EXCHANGE_EWS_URL,
        username=settings.RESPA_EXCHANGE_EWS_USERNAME,
        password=settings.RESPA_EXCHANGE_EWS_PASSWORD,
    )
