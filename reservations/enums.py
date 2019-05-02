from django.utils.translation import ugettext_lazy as _
from enumfields import Enum


class WinterStorageMethod(Enum):
    ON_TRESTLES = "on_trestles"
    ON_TRAILER = "on_trailer"

    class Labels:
        ON_TRESTLES = _("On trestles")
        ON_TRAILER = _("On a trailer")
