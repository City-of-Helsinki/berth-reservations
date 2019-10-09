from unittest.mock import MagicMock

from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django_ilmoitin.dummy_context import dummy_context
from django_ilmoitin.registry import notifications
from enumfields import Enum

from .utils import localize_datetime


class NotificationType(Enum):
    BERTH_RESERVATION_CREATED = "berth_reservation_created"
    WINTER_STORAGE_RESERVATION_CREATED = "winter_storage_reservation_created"

    class Labels:
        BERTH_RESERVATION_CREATED = _("Berth reservation created")
        WINTER_STORAGE_RESERVATION_CREATED = _("Winter storage reservation created")


notifications.register(
    NotificationType.BERTH_RESERVATION_CREATED.value,
    NotificationType.BERTH_RESERVATION_CREATED.label,
)
notifications.register(
    NotificationType.WINTER_STORAGE_RESERVATION_CREATED.value,
    NotificationType.WINTER_STORAGE_RESERVATION_CREATED.label,
)

dummy_context.context.update(
    {
        "created_at": localize_datetime(timezone.now()),
        # TODO: pass more appropriate in-memory objects
        "reservation": MagicMock(),
    }
)
