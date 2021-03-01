from babel.dates import format_date
from dateutil.utils import today
from django_ilmoitin.dummy_context import COMMON_CONTEXT, dummy_context

from ..tests.factories import (
    BerthApplicationFactory,
    HarborChoiceFactory,
    WinterAreaChoiceFactory,
    WinterStorageApplicationFactory,
)
from .types import NotificationType


def load_dummy_context():
    berth_application = BerthApplicationFactory.build()
    harbor_choices = HarborChoiceFactory.build_batch(
        size=3, application=berth_application
    )
    winter_storage_application = WinterStorageApplicationFactory.build()
    winter_area_choices = WinterAreaChoiceFactory.build_batch(
        size=3, application=winter_storage_application
    )

    dummy_context.update(
        {
            COMMON_CONTEXT: {"created_at": format_date(today(), locale="fi")},
            NotificationType.BERTH_APPLICATION_CREATED: {
                "subject": NotificationType.BERTH_APPLICATION_CREATED.label,
                "application": berth_application,
                "harbor_choices": sorted(harbor_choices, key=lambda c: c.priority),
            },
            NotificationType.BERTH_APPLICATION_REJECTED: {
                "subject": NotificationType.BERTH_APPLICATION_REJECTED.label,
                "application": berth_application,
                "harbor_choices": sorted(harbor_choices, key=lambda c: c.priority),
            },
            NotificationType.WINTER_STORAGE_APPLICATION_CREATED: {
                "subject": NotificationType.WINTER_STORAGE_APPLICATION_CREATED.label,
                "application": winter_storage_application,
                "area_choices": sorted(winter_area_choices, key=lambda c: c.priority),
            },
            NotificationType.UNMARKED_WINTER_STORAGE_APPLICATION_CREATED: {
                "subject": NotificationType.UNMARKED_WINTER_STORAGE_APPLICATION_CREATED.label,
                "application": winter_storage_application,
                "area_choices": sorted(winter_area_choices, key=lambda c: c.priority),
            },
        }
    )
