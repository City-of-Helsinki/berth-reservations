from django.db.models import IntegerChoices, TextChoices
from django.utils.translation import gettext_lazy as _

from berth_reservations.mixins import ChoicesMixin


class WinterStorageMethod(ChoicesMixin, TextChoices):
    ON_TRESTLES = "on_trestles", _("On trestles")
    ON_TRAILER = "on_trailer", _("On a trailer")
    UNDER_TARP = "under_tarp", _("Under a tarp")


class ApplicationStatus(ChoicesMixin, TextChoices):
    PENDING = "pending", _("Pending")
    OFFER_GENERATED = "offer_generated", _("Offer generated")
    OFFER_SENT = "offer_sent", _("Offer sent")
    NO_SUITABLE_BERTHS = "no_suitable_berths", _("No suitable berths")
    HANDLED = "handled", _("Handled")
    REJECTED = "rejected", _("Rejected")
    EXPIRED = "expired", _("Expired")


class ApplicationAreaType(ChoicesMixin, TextChoices):
    MARKED = "marked", _("Marked")
    UNMARKED = "unmarked", _("Unmarked")


class ApplicationPriority(ChoicesMixin, IntegerChoices):
    LOW = 0, _("Low")
    MEDIUM = 1, _("Medium")
    HIGH = 2, _("High")
