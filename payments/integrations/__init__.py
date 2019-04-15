from .bambora_payform import BamboraPayformPayments


_payment_provider = None


def get_payment_provider():
    global _payment_provider
    if not _payment_provider:
        # TODO where/how should we choose this?
        _payment_provider = BamboraPayformPayments()
    return _payment_provider
