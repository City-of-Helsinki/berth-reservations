from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class WinterStorageMethod(TextChoices):
    ON_TRESTLES = "on_trestles", _("On trestles")
    ON_TRAILER = "on_trailer", _("On a trailer")
    UNDER_TARP = "under_tarp", _("Under a tarp")


class ApplicationStatus(TextChoices):
    PENDING = "pending", _("Pending")
    OFFER_GENERATED = "offer_generated", _("Offer generated")
    OFFER_SENT = "offer_sent", _("Offer sent")
    NO_SUITABLE_BERTHS = "no_suitable_berths", _("No suitable berths")
    HANDLED = "handled", _("Handled")
    REJECTED = "rejected", _("Rejected")
    EXPIRED = "expired", _("Expired")


class ApplicationAreaType(TextChoices):
    MARKED = "marked", _("Marked")
    UNMARKED = "unmarked", _("Unmarked")
