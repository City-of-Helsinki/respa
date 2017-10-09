from six import string_types

from .xml import S, T


class EWSRequest(object):
    """
    Encapsulates an Exchange Web Services (EWS) request.
    """
    version = "Exchange2010"

    def __init__(self, body, impersonation=None):
        """
        Initialize the request.

        :param body: Lxml element. The actual SOAP message.
        :param impersonation: Impersonation information.
                              Currently supported is passing
                              the impersonatee's SMTP address,
                              or a raw `ExchangeImpersonation`
                              element.
        """
        self.body = body
        self.impersonation = impersonation

    def envelop(self):
        """
        Get this request's body enveloped for SOAP usage.

        :return: A bar of soap
        """
        if isinstance(self.impersonation, string_types):
            impersonation = T.ExchangeImpersonation(
                T.ConnectingSID(
                    T.SmtpAddress(self.impersonation)
                )
            )
        else:
            impersonation = self.impersonation

        return S.Envelope(
            S.Header(*[e for e in [
                T.RequestServerVersion(Version=self.version),
                impersonation
            ] if e is not None]),
            S.Body(self.body)
        )

    def send(self, sess):
        """
        Send this request and return appropriately mangled response content.

        :param sess: The EWSSession to send this request with.
        :return:
        """
        raise NotImplementedError("%r does not implement send()" % self)  # pragma: no cover
