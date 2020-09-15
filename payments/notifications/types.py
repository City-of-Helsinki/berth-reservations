from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class NotificationType(TextChoices):
    ORDER_APPROVED = (
        "order_approved",
        _("Order approved"),
    )
