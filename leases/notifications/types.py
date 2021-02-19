from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class NotificationType(TextChoices):
    AUTOMATIC_INVOICING_EMAIL_ADMINS = (
        "automatic_invoicing_email_admins",
        _("Next season invoices sent"),
    )
    BERTH_LEASE_TERMINATED_LEASE_NOTICE = (
        "berth_lease_terminated_lease_notice",
        _("Terminated berth lease"),
    )
