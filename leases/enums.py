from django.utils.translation import ugettext_lazy as _
from enumfields import Enum


class LeaseStatus(Enum):
    OFFERED = "offered"
    REFUSED = "refused"
    EXPIRED = "expired"
    PAID = "paid"

    class Labels:
        OFFERED = _("Offered")
        REFUSED = _("Refused")
        EXPIRED = _("Expired")
        PAID = _("Paid")
