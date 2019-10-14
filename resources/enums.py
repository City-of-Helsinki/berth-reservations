from django.utils.translation import ugettext_lazy as _
from enumfields import IntEnum


class BerthMooringType(IntEnum):
    # In Finnish: "ILMAN PERÄKIINNITYSTÄ"
    NO_STERN_TO_MOORING = 1
    # In Finnish: "AISAPAIKKA"
    SINGLE_SLIP_PLACE = 2
    # In Finnish: "KÄVELYAISAPAIKKA"
    SIDE_SLIP_PLACE = 3
    # In Finnish: "PERÄPOIJUPAIKKA"
    STERN_BUOY_PLACE = 4
    # In Finnish: "PAALUPERÄKIINNITYS"
    STERN_POLE_MOORING = 5
    # In Finnish: "SIVUKIINNITYS"
    QUAYSIDE_MOORING = 6
    # In Finnish: "JOLLAPAIKKA"
    DINGHY_PLACE = 7
    # In Finnish: "POIJU (MERELLÄ)"
    SEA_BUOY_MOORING = 8
    # In Finnish: "TRAILERIPAIKKA"
    TRAWLER_PLACE = 9

    class Labels:
        NO_STERN_TO_MOORING = _("No stern-to mooring")
        SINGLE_SLIP_PLACE = _("Single slip place")
        SIDE_SLIP_PLACE = _("Side slip place")
        STERN_BUOY_PLACE = _("Stern buoy place")
        STERN_POLE_MOORING = _("Stern pole mooring")
        QUAYSIDE_MOORING = _("Quayside mooring")
        DINGHY_PLACE = _("Dinghy place")
        SEA_BUOY_MOORING = _("Sea buoy mooring")
        TRAWLER_PLACE = _("Trawler place")
