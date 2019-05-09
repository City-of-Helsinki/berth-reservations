from django.utils.translation import ugettext_lazy as _
from enumfields import Enum


class NotificationType(Enum):
    BERTH_RESERVATION_CREATED = "berth_reservation_created"

    class Labels:
        BERTH_RESERVATION_CREATED = _("Berth reservation created")
