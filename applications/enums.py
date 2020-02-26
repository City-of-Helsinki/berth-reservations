from django.utils.translation import ugettext_lazy as _
from enumfields import Enum


class WinterStorageMethod(Enum):
    ON_TRESTLES = "on_trestles"
    ON_TRAILER = "on_trailer"
    UNDER_TARP = "under_tarp"

    class Labels:
        ON_TRESTLES = _("On trestles")
        ON_TRAILER = _("On a trailer")
        UNDER_TARP = _("Under a tarp")


class ApplicationStatus(Enum):
    PENDING = "pending"
    OFFER_GENERATED = "offer_generated"
    OFFER_SENT = "offer_sent"
    NO_SUITABLE_BERTHS = "no_suitable_berths"
    NO_SUITABLE_BERTHS_NOTIFIED = "no_suitable_berths_notified"
    HANDLED = "handled"
    EXPIRED = "expired"

    class Labels:
        PENDING = _("Pending")
        OFFER_GENERATED = _("Offer generated")
        OFFER_SENT = _("Offer sent")
        NO_SUITABLE_BERTHS = _("No suitable berths")
        NO_SUITABLE_BERTHS_NOTIFIED = _("Notified that there are no suitable berths")
        HANDLED = _("Handled")
        EXPIRED = _("Expired")
