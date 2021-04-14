from django.db.models import IntegerChoices, TextChoices
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
    STORAGE_ON_ICE = ("storage_on_ice", _("Storage on ice"))
    PARKING_PERMIT = "parking_permit", _("Parking permit")
    DINGHY_PLACE = "dinghy_place", _("Dinghy place")

    @staticmethod
    def FIXED_SERVICES():
        return [
            ProductServiceType.ELECTRICITY,
            ProductServiceType.GATE,
            ProductServiceType.LIGHTING,
            ProductServiceType.MOORING,
            ProductServiceType.WASTE_COLLECTION,
            ProductServiceType.WATER,
        ]

    @staticmethod
    def OPTIONAL_SERVICES():
        return [
            ProductServiceType.DINGHY_PLACE,
            ProductServiceType.PARKING_PERMIT,
            ProductServiceType.STORAGE_ON_ICE,
            ProductServiceType.SUMMER_STORAGE_FOR_DOCKING_EQUIPMENT,
            ProductServiceType.SUMMER_STORAGE_FOR_TRAILERS,
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
    DRAFTED = "drafted", _("Drafted")
    OFFERED = "offered", _("Offered")
    REJECTED = "rejected", _("Rejected")
    CANCELLED = "cancelled", _("Cancelled")
    EXPIRED = "expired", _("Expired")
    ERROR = "error", _("Error")
    PAID = "paid", _("Paid")
    PAID_MANUALLY = "paid_man", _("Paid manually")  # max 9 chars
    REFUNDED = "refunded", _("Refunded")

    @classmethod
    def get_waiting_statuses(cls):
        return (cls.DRAFTED, cls.OFFERED)

    @classmethod
    def get_paid_statuses(cls):
        return (cls.PAID, cls.PAID_MANUALLY)


class OfferStatus(TextChoices):
    DRAFTED = "drafted", _("Drafted")
    OFFERED = "offered", _("Offered")
    ACCEPTED = "accepted", _("Accepted")
    REJECTED = "rejected", _("Rejected")
    EXPIRED = "expired", _("Expired")
    CANCELLED = "cancelled", _("Cancelled")


class OrderRefundStatus(TextChoices):
    PENDING = "pending", _("Pending")
    ACCEPTED = "accepted", _("Accepted")
    REJECTED = "rejected", _("Rejected")


class OrderType(TextChoices):
    LEASE_ORDER = "lease_order", _("Lease order")
    ADDITIONAL_PRODUCT_ORDER = "additional_product_order", _("Additional product order")


class LeaseOrderType(TextChoices):
    NEW_BERTH_ORDER = "new_berth_order", _("New berth order")
    RENEW_BERTH_ORDER = "renew_berth_order", _("Renew berth order")
    BERTH_SWITCH_ORDER = "berth_switch_order", _("Berth switch order")
    WINTER_STORAGE_ORDER = "winter_storage_order", _("Winter storage order")
    UNMARKED_WINTER_STORAGE_ORDER = (
        "unmarked_winter_storage_order",
        _("Unmarked winter storage order"),
    )
    INVALID = "invalid_order", _("Invalid order")


class PriceTier(IntegerChoices):
    TIER_1 = 1, _("Tier 1")
    TIER_2 = 2, _("Tier 2")
    TIER_3 = 3, _("Tier 3")
