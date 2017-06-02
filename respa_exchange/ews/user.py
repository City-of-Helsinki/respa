from .base import EWSRequest
from .xml import M, NAMESPACES, T


class ResolveNamesRequest(EWSRequest):
    """
    An EWS request to resolve email addresses and display names.
    """

    def __init__(self, names, principal=None):
        """
        Initialize the request.

        :param names: The list of names to resolve.
        """
        body = M.ResolveNames(
            {'ReturnFullContactData': 'true'},
            *[M.UnresolvedEntry(x) for x in names]
        )
        kwargs = {}
        if principal:
            kwargs['impersonation'] = principal
        super().__init__(body, **kwargs)

    def send(self, sess):
        """
        Send the resolve request, and return a list of user info objects.

        :type sess: respa_exchange.session.ExchangeSession
        """
        resp = sess.soap(self)
        resolutions = resp.xpath("//t:Resolution", namespaces=NAMESPACES)
        return resolutions


class GetDelegateRequest(EWSRequest):
    """
    An EWS request to get delegates allowed to access a mailbox.
    """

    def __init__(self, email, principal=None):
        """
        Initialize the request.

        :param email: Email address of the user to query.
        """
        body = M.GetDelegate(
            {'IncludePermissions': 'true'},
            M.Mailbox(T.EmailAddress(email))
        )
        kwargs = {}
        if principal:
            kwargs['impersonation'] = principal
        super().__init__(body, **kwargs)

    def send(self, sess):
        """
        Send the resolve request, and return a list of user info objects.

        :type sess: respa_exchange.session.ExchangeSession
        """
        resp = sess.soap(self)
        resolutions = resp.xpath("//t:Resolution", namespaces=NAMESPACES)
        return resolutions
