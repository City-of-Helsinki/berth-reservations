from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class NotificationType(TextChoices):
    AUTOMATIC_INVOICING_EMAIL_ADMINS = (
        "automatic_invoicing_email_admins",
        _("Next season invoices sent"),
    )
