from django.utils.translation import ugettext_lazy as _
from enumfields import Enum


class ServiceType(Enum):
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
            ServiceType.ELECTRICITY,
            ServiceType.WATER,
            ServiceType.GATE,
            ServiceType.MOORING,
            ServiceType.WASTE_COLLECTION,
            ServiceType.LIGHTING,
        ]

    @staticmethod
    def OPTIONAL_SERVICES():
        return [
            ServiceType.SUMMER_STORAGE_FOR_DOCKING_EQUIPMENT,
            ServiceType.SUMMER_STORAGE_FOR_TRAILERS,
            ServiceType.PARKING_PERMIT,
            ServiceType.DINGHY_PLACE,
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
