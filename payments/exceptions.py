class VenepaikkaPaymentError(Exception):
    """Base for payment specific exceptions"""


class OrderStatusTransitionError(VenepaikkaPaymentError):
    """Attempting an Order from-to status transition that isn't allowed"""


class ServiceUnavailableError(VenepaikkaPaymentError):
    """When payment service is unreachable, offline for maintenance etc"""


class PayloadValidationError(VenepaikkaPaymentError):
    """When something is wrong or missing in the posted payment payload data"""


class DuplicateOrderError(VenepaikkaPaymentError):
    """If order with the same ID has already been previously posted"""


class UnknownReturnCodeError(VenepaikkaPaymentError):
    """If payment service returns a status code that is not recognized by the handler"""


class ExpiredOrderError(VenepaikkaPaymentError):
    """If the Order is being paid after the due date"""


class PaymentNotFoundError(VenepaikkaPaymentError):
    """When the payment cannot be found on Bambora's system"""


class RefundPriceError(VenepaikkaPaymentError):
    """When the amount to be refunded (taken from Bambora) is different than the price of the order"""


class TalpaProductAccountingNotFoundError(VenepaikkaPaymentError):
    """When the TalpaProductAccounting for the order can't be found"""
