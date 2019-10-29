from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django_ilmoitin.dummy_context import COMMON_CONTEXT, dummy_context
from django_ilmoitin.registry import notifications
from enumfields import Enum

from .tests.factories import (
    BerthReservationFactory,
    HarborChoiceFactory,
    WinterAreaChoiceFactory,
    WinterStorageReservationFactory,
)
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

berth_reservation = BerthReservationFactory.build()
harbor_choices = HarborChoiceFactory.build_batch(size=3, reservation=berth_reservation)
winter_storage_reservation = WinterStorageReservationFactory.build()
winter_area_choices = WinterAreaChoiceFactory.build_batch(
    size=3, reservation=winter_storage_reservation
)

dummy_context.update(
    {
        COMMON_CONTEXT: {"created_at": localize_datetime(timezone.now())},
        NotificationType.BERTH_RESERVATION_CREATED: {
            "reservation": berth_reservation,
            "harbor_choices": sorted(harbor_choices, key=lambda c: c.priority),
        },
        NotificationType.WINTER_STORAGE_RESERVATION_CREATED: {
            "reservation": winter_storage_reservation,
            "area_choices": sorted(winter_area_choices, key=lambda c: c.priority),
        },
    }
)
