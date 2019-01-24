from anymail.exceptions import AnymailError
from django.conf import settings
from django.dispatch import Signal, receiver
from raven import Client

from notifications.enums import NotificationType
from notifications.utils import send_notification


reservation_saved = Signal(providing_args=['reservation'])


@receiver(reservation_saved)
def reservation_notification_handler(sender, reservation, **kwargs):
    try:
        send_notification(
            reservation.email,
            NotificationType.RESERVATION_CREATED,
            reservation.get_notification_context(),
            reservation.language
        )
    except (OSError, AnymailError):
        raven_client = Client()
        raven_client.captureException()


if settings.NOTIFICATIONS_ENABLED:
    reservation_saved.connect(reservation_notification_handler)
