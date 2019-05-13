from anymail.exceptions import AnymailError
from django.conf import settings
from django.dispatch import Signal
from raven import Client

from notifications.enums import NotificationType
from notifications.utils import send_notification

reservation_saved = Signal(providing_args=["reservation"])


def reservation_notification_handler(sender, reservation, **kwargs):
    notification_type = NotificationType.BERTH_RESERVATION_CREATED
    if sender == "CreateWinterStorageReservation":
        notification_type = NotificationType.WINTER_STORAGE_RESERVATION_CREATED
    try:
        send_notification(
            reservation.email,
            notification_type,
            reservation.get_notification_context(),
            reservation.language,
        )
    except (OSError, AnymailError):
        raven_client = Client()
        raven_client.captureException()


if settings.NOTIFICATIONS_ENABLED:
    reservation_saved.connect(reservation_notification_handler)
