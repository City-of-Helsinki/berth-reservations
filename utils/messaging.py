from django.utils.translation import gettext_lazy as _


def get_email_subject(notification_type):
    from applications.notifications import (
        NotificationType as ApplicationsNotificationType,
    )
    from payments.notifications import NotificationType as PaymentsNotificationType

    if (
        notification_type == PaymentsNotificationType.NEW_BERTH_ORDER_APPROVED
        or notification_type == PaymentsNotificationType.RENEW_BERTH_ORDER_APPROVED
    ):
        return _("Boat berth invoice")
    elif notification_type == PaymentsNotificationType.ORDER_CANCELLED:
        return _("Confirmation")
    elif notification_type == PaymentsNotificationType.ORDER_REFUNDED:
        return _("Refund confirmation")
    elif notification_type == ApplicationsNotificationType.BERTH_APPLICATION_REJECTED:
        return _("Berth application processed")
    return notification_type.label
