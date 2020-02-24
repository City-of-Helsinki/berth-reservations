from anymail.exceptions import AnymailError
from django.conf import settings
from django.dispatch import Signal
from django_ilmoitin.utils import send_notification
from sentry_sdk import capture_exception

from .notifications import NotificationType

application_saved = Signal(providing_args=["application"])


def application_notification_handler(sender, application, **kwargs):
    notification_type = NotificationType.BERTH_APPLICATION_CREATED.value
    if sender == "CreateWinterStorageApplication":
        notification_type = NotificationType.WINTER_STORAGE_APPLICATION_CREATED.value
    try:
        send_notification(
            application.email,
            notification_type,
            application.get_notification_context(),
            application.language,
        )
    except (OSError, AnymailError) as e:
        capture_exception(e)


if settings.NOTIFICATIONS_ENABLED:
    application_saved.connect(
        application_notification_handler, dispatch_uid="application_saved"
    )
