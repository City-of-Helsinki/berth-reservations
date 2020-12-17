from random import randint

from django_ilmoitin.dummy_context import dummy_context

from .types import NotificationType


def load_dummy_context():
    dummy_context.update(
        {
            NotificationType.AUTOMATIC_INVOICING_EMAIL_ADMINS: {
                "subject": NotificationType.AUTOMATIC_INVOICING_EMAIL_ADMINS.label,
                "exited_with_errors": False,
                "successful_orders": randint(100, 500),
                "failed_orders": randint(0, 10),
            }
        }
    )
