from anymail.exceptions import AnymailError
from django.conf import settings
from django.dispatch import Signal
from raven import Client

from notifications.enums import NotificationType
from notifications.utils import send_notification


reservation_saved = Signal()


def reservation_notification_handler(sender, **kwargs):
    try:
        send_notification(
            sender.email,
            NotificationType.RESERVATION_CREATED,
            sender.get_notification_context(),
            sender.language
        )
    except (OSError, AnymailError):
        raven_client = Client()
        raven_client.captureException()


if settings.NOTIFICATIONS_ENABLED:
    reservation_saved.connect(reservation_notification_handler)
