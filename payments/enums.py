from django.utils.translation import ugettext_lazy as _
from enumfields import Enum


class ProductServiceType(Enum):
    # Fixed services
    ELECTRICITY = "electricity"
    WATER = "water"
    GATE = "gate"
    MOORING = "mooring"
    WASTE_COLLECTION = "waste_collection"
    LIGHTING = "lighting"

    # Optional Services
    SUMMER_STORAGE_FOR_DOCKING_EQUIPMENT = "summer_storage_for_docking_equipment"
    SUMMER_STORAGE_FOR_TRAILERS = "summer_storage_for_trailers"
    PARKING_PERMIT = "parking_permit"
    DINGHY_PLACE = "dinghy_place"

    class Labels:
        ELECTRICITY = _("Electricity")
        WATER = _("Water")
        GATE = _("Gate")
        MOORING = _("Mooring")
        WASTE_COLLECTION = _("Waste collection")
        LIGHTING = _("Lighting")
        SUMMER_STORAGE_FOR_DOCKING_EQUIPMENT = _("Summer storage for docking equipment")
        SUMMER_STORAGE_FOR_TRAILERS = _("Summer storage for trailers")
        PARKING_PERMIT = _("Parking permit")
        DINGHY_PLACE = _("Dinghy place")

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

    def is_fixed_service(self):
        return self in self.FIXED_SERVICES()

    def is_optional_service(self):
        return self in self.OPTIONAL_SERVICES()


class AdditionalProductType(Enum):
    FIXED_SERVICE = "fixed_service"
    OPTIONAL_SERVICE = "optional_service"

    class Labels:
        FIXED_SERVICE = _("Fixed service")
        OPTIONAL_SERVICE = _("Optional service")


class PeriodType(Enum):
    YEAR = "year"
    SEASON = "season"
    MONTH = "month"

    class Labels:
        YEAR = _("Year")
        SEASON = _("Season")
        MONTH = _("Month")


class PriceUnits(Enum):
    AMOUNT = "amount"
    PERCENTAGE = "percentage"

    class Labels:
        AMOUNT = _("Amount")
        PERCENTAGE = _("Percentage")


class OrderStatus(Enum):
    WAITING = "waiting"
    REJECTED = "rejected"
    EXPIRED = "expired"
    PAID = "paid"

    class Labels:
        WAITING = _("Waiting")
        REJECTED = _("Rejected")
        EXPIRED = _("Expired")
        PAID = _("Paid")
