from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_ilmoitin.dummy_context import COMMON_CONTEXT, dummy_context
from django_ilmoitin.registry import notifications
from enumfields import Enum

from .tests.factories import (
    BerthApplicationFactory,
    HarborChoiceFactory,
    WinterAreaChoiceFactory,
    WinterStorageApplicationFactory,
)
from .utils import localize_datetime


class NotificationType(Enum):
    BERTH_APPLICATION_CREATED = "berth_application_created"
    WINTER_STORAGE_APPLICATION_CREATED = "winter_storage_application_created"

    class Labels:
        BERTH_APPLICATION_CREATED = _("Berth application created")
        WINTER_STORAGE_APPLICATION_CREATED = _("Winter storage application created")


notifications.register(
    NotificationType.BERTH_APPLICATION_CREATED.value,
    NotificationType.BERTH_APPLICATION_CREATED.label,
)
notifications.register(
    NotificationType.WINTER_STORAGE_APPLICATION_CREATED.value,
    NotificationType.WINTER_STORAGE_APPLICATION_CREATED.label,
)

berth_application = BerthApplicationFactory.build()
harbor_choices = HarborChoiceFactory.build_batch(size=3, application=berth_application)
winter_storage_application = WinterStorageApplicationFactory.build()
winter_area_choices = WinterAreaChoiceFactory.build_batch(
    size=3, application=winter_storage_application
)

dummy_context.update(
    {
        COMMON_CONTEXT: {"created_at": localize_datetime(timezone.now())},
        NotificationType.BERTH_APPLICATION_CREATED: {
            "application": berth_application,
            "harbor_choices": sorted(harbor_choices, key=lambda c: c.priority),
        },
        NotificationType.WINTER_STORAGE_APPLICATION_CREATED: {
            "application": winter_storage_application,
            "area_choices": sorted(winter_area_choices, key=lambda c: c.priority),
        },
    }
)
