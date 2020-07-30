from django.utils.translation import gettext_lazy as _
from enumfields import Enum


class LeaseStatus(Enum):
    DRAFTED = "drafted"
    OFFERED = "offered"
    REFUSED = "refused"
    EXPIRED = "expired"
    PAID = "paid"

    class Labels:
        DRAFTED = _("Drafted")
        OFFERED = _("Offered")
        REFUSED = _("Refused")
        EXPIRED = _("Expired")
        PAID = _("Paid")
