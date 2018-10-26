from django.utils.translation import ugettext_lazy as _
from enumfields import Enum


class NotificationType(Enum):
    RESERVATION_CREATED = 'reservation_created'

    class Labels:
        RESERVATION_CREATED = _('Reservation created')
