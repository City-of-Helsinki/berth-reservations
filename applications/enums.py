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
    NO_SUITABLE_BERTHS_NOTIFIED = (
        "no_suitable_berths_notified",
        _("Notified that there are no suitable berths"),
    )
    HANDLED = "handled", _("Handled")
    EXPIRED = "expired", _("Expired")
