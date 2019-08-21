from anymail.exceptions import AnymailError
from django.conf import settings
from django.dispatch import Signal
from django_ilmoitin.utils import send_notification
from sentry_sdk import capture_exception

from .notifications import NotificationType

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
    except (OSError, AnymailError) as e:
        capture_exception(e)


if settings.NOTIFICATIONS_ENABLED:
    reservation_saved.connect(reservation_notification_handler)
