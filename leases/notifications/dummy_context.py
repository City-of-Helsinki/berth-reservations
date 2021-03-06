from random import randint

from babel.dates import format_date
from dateutil.utils import today
from django_ilmoitin.dummy_context import dummy_context

from ..tests.factories import BerthLeaseFactory, WinterStorageLeaseFactory
from .types import NotificationType


def load_dummy_context():
    berth_lease = BerthLeaseFactory.build()
    ws_lease = WinterStorageLeaseFactory.build()

    dummy_context.update(
        {
            NotificationType.AUTOMATIC_INVOICING_EMAIL_ADMINS: {
                "subject": NotificationType.AUTOMATIC_INVOICING_EMAIL_ADMINS.label,
                "exited_with_errors": False,
                "successful_orders": randint(100, 500),
                "failed_orders": randint(0, 10),
            },
            NotificationType.BERTH_LEASE_TERMINATED_LEASE_NOTICE: {
                "subject": NotificationType.BERTH_LEASE_TERMINATED_LEASE_NOTICE.label,
                "cancelled_at": format_date(today(), locale="fi"),
                "lease": berth_lease,
            },
            NotificationType.WINTER_STORAGE_LEASE_TERMINATED_LEASE_NOTICE: {
                "subject": NotificationType.WINTER_STORAGE_LEASE_TERMINATED_LEASE_NOTICE.label,
                "cancelled_at": format_date(today(), locale="fi"),
                "lease": ws_lease,
            },
        }
    )
