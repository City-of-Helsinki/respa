import sys
import types

from django.utils.crypto import get_random_string
from lxml import etree
from requests.models import Response

from respa_exchange.ews.session import ExchangeSession
from respa_exchange.ews.xml import S


def iter_content(self, *args, **kwargs):
    """
    Monkey-patched version of Response.iter_content()
    """
    yield self._content


class SoapSeller(ExchangeSession):
    """
    The SoapSeller ("saippuakauppias") is a special ExchangeSession object for testing.

    Handler delegate classes should be objects with functions whose names begin with
    `handle_`; those handlers should accept SOAP request envelopes as Etrees and return
    SOAP response envelopes as Etrees.

    """

    def __init__(self, handler_delegate):
        """
        Construct a SoapSeller using the given delegate object.

        :param handler_delegate: The delegate object; see the class docstring.
        """
        super(SoapSeller, self).__init__("http://example.com", "CONTOSO\\dummy", "dummy")
        self.handler_delegate = handler_delegate

    def send(self, request, **kwargs):
        """
        Send a requests PreparedRequest. (Override of the super-superclass's method)

        :type request: requests.models.PreparedRequest
        """
        assert request.method == "POST"  # Soap sellers don't do GET
        xml = etree.XML(request.body)
        for handler in self._get_handlers_from_delegate():
            handler_rv = handler(xml)
            if handler_rv is None:
                continue
            return self._postprocess_handler_response(request, handler_rv)
        raise ValueError("No SoapSeller handler could deal with %r" % request.body)  # pragma: no cover

    def _get_handlers_from_delegate(self):
        for name in dir(self.handler_delegate):
            if name.startswith("handle_"):
                yield getattr(self.handler_delegate, name)

    def _postprocess_handler_response(self, request, handler_rv):
        if isinstance(handler_rv, Response):  # Direct response (could be useful)
            return handler_rv  # pragma: no cover
        envelope = S.Envelope(
            S.Header(),  # TODO: Fill me in?
            S.Body(handler_rv)
        )
        handler_rv = Response()
        handler_rv.request = request
        handler_rv.status_code = 200
        handler_rv.headers = {
            "Content-Type": "text/xml; encoding=UTF-8",
        }
        handler_rv._content = etree.tostring(envelope, encoding="utf-8", pretty_print=True)
        # Make iter_content work for streaming
        handler_rv.iter_content = types.MethodType(iter_content, handler_rv)
        return handler_rv

    @classmethod
    def wire(cls, settings, handler_delegate):
        """
        Wire up SoapSeller with the given handler delegate in the given `settings`.

        :param settings: Settings monkeypatch object
        """
        id = "get_wired_soap_seller_%s" % get_random_string()

        def getter(**kwargs):
            return cls(handler_delegate)

        setattr(sys.modules[__name__], id, getter)
        settings.RESPA_EXCHANGE_EWS_SESSION_CLASS = "%s.%s" % (__name__, id)
