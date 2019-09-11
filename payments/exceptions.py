

class RespaPaymentError(Exception):
    """Base for payment specific exceptions"""


class OrderStateTransitionError(RespaPaymentError):
    """Attempting an Order from-to -state transition that isn't allowed"""


class ServiceUnavailableError(RespaPaymentError):
    """When payment service is unreachable, offline for maintenance etc"""


class PayloadValidationError(RespaPaymentError):
    """When something is wrong or missing in the posted payment payload data"""


class DuplicateOrderError(RespaPaymentError):
    """If order with the same ID has already been previously posted"""


class UnknownReturnCodeError(RespaPaymentError):
    """If payment service returns a status code that is not recognized by the handler"""
