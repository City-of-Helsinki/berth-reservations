from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class NotificationType(TextChoices):
    NEW_BERTH_ORDER_APPROVED = (
        "new_berth_order_approved",
        _("New berth order approved"),
    )
    RENEW_BERTH_ORDER_APPROVED = (
        "renew_berth_order_approved",
        _("Renew berth order approved"),
    )
    BERTH_SWITCH_ORDER_APPROVED = (
        "berth_switch_order_approved",
        _("Berth switch order approved"),
    )
    NEW_WINTER_STORAGE_ORDER_APPROVED = (
        "new_winter_storage_order_approved",
        _("New winter storage order approved"),
    )
    UNMARKED_WINTER_STORAGE_ORDER_APPROVED = (
        "unmarked_winter_storage_order_approved",
        _("Unmarked winter storage order approved"),
    )
    ADDITIONAL_PRODUCT_ORDER_APPROVED = (
        "additional_product_order_approved",
        _("Additional product order approved"),
    )
    ORDER_CANCELLED = ("order_cancelled", _("Order cancelled"))
