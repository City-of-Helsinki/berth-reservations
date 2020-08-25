from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class LeaseStatus(TextChoices):
    DRAFTED = "drafted", _("Drafted")
    OFFERED = "offered", _("Offered")
    REFUSED = "refused", _("Refused")
    EXPIRED = "expired", _("Expired")
    PAID = "paid", _("Paid")
