from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class LeaseStatus(TextChoices):
    DRAFTED = "drafted", _("Drafted")
    OFFERED = "offered", _("Offered")
    REFUSED = "refused", _("Refused")
    EXPIRED = "expired", _("Expired")
    ERROR = "error", _("Error")
    PAID = "paid", _("Paid")
    TERMINATED = "terminated", _("Terminated")
