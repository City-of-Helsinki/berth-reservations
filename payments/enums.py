from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class ProductServiceType(TextChoices):
    # Fixed services
    ELECTRICITY = "electricity", _("Electricity")
    WATER = "water", _("Water")
    GATE = "gate", _("Gate")
    MOORING = "mooring", _("Mooring")
    WASTE_COLLECTION = "waste_collection", _("Waste collection")
    LIGHTING = "lighting", _("Lighting")

    # Optional Services
    SUMMER_STORAGE_FOR_DOCKING_EQUIPMENT = (
        "summer_storage_for_docking_equipment",
        _("Summer storage for docking equipment"),
    )
    SUMMER_STORAGE_FOR_TRAILERS = (
        "summer_storage_for_trailers",
        _("Summer storage for trailers"),
    )
    PARKING_PERMIT = "parking_permit", _("Parking permit")
    DINGHY_PLACE = "dinghy_place", _("Dinghy place")

    @staticmethod
    def FIXED_SERVICES():
        return [
            ProductServiceType.ELECTRICITY,
            ProductServiceType.WATER,
            ProductServiceType.GATE,
            ProductServiceType.MOORING,
            ProductServiceType.WASTE_COLLECTION,
            ProductServiceType.LIGHTING,
        ]

    @staticmethod
    def OPTIONAL_SERVICES():
        return [
            ProductServiceType.SUMMER_STORAGE_FOR_DOCKING_EQUIPMENT,
            ProductServiceType.SUMMER_STORAGE_FOR_TRAILERS,
            ProductServiceType.PARKING_PERMIT,
            ProductServiceType.DINGHY_PLACE,
        ]


class AdditionalProductType(TextChoices):
    FIXED_SERVICE = "fixed_service", _("Fixed service")
    OPTIONAL_SERVICE = "optional_service", _("Optional service")


class PeriodType(TextChoices):
    YEAR = "year", _("Year")
    SEASON = "season", _("Season")
    MONTH = "month", _("Month")


class PriceUnits(TextChoices):
    AMOUNT = "amount", _("Amount")
    PERCENTAGE = "percentage", _("Percentage")


class OrderStatus(TextChoices):
    WAITING = "waiting", _("Waiting")
    REJECTED = "rejected", _("Rejected")
    CANCELLED = "cancelled", _("Cancelled")
    EXPIRED = "expired", _("Expired")
    PAID = "paid", _("Paid")


class OrderType(TextChoices):
    NEW_BERTH_ORDER = "new_berth_order", _("New berth order")
    RENEW_BERTH_ORDER = "renew_berth_order", _("Renew berth order")
    BERTH_SWITCH_ORDER = "berth_switch_order", _("Berth switch order")
    WINTER_STORAGE_ORDER = "winter_storage_order", _("Winter storage order")
    UNMARKED_WINTER_STORAGE_ORDER = (
        "unmarked_winter_storage_order",
        _("Unmarked winter storage order"),
    )
    INVALID = "invalid_order", _("Invalid order")
