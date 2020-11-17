from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class ContractStatus(TextChoices):
    NEW = "new", _("New")
    PENDING = "pending", _("Pending")
    SIGNED = "signed", _("Signed")
    DELETED = "deleted", _("Deleted")
    CANCELLED = "cancelled", _("Cancelled")
