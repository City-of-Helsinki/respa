from django.conf import settings

from respa_exchange.ews.session import ExchangeSession


def get_ews_session():
    # TODO: Maybe cache or something? NTLM handshakes can take some time...
    return ExchangeSession(
        url=settings.RESPA_EXCHANGE_EWS_URL,
        username=settings.RESPA_EXCHANGE_EWS_USERNAME,
        password=settings.RESPA_EXCHANGE_EWS_PASSWORD,
    )
