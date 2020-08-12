class VenepaikkaPaymentError(Exception):
    """Base for payment specific exceptions"""


class OrderStatusTransitionError(VenepaikkaPaymentError):
    """Attempting an Order from-to status transition that isn't allowed"""
