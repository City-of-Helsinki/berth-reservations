from django.db.models import IntegerChoices, TextChoices
from django.utils.translation import gettext_lazy as _

from berth_reservations.mixins import ChoicesMixin


class BerthMooringType(ChoicesMixin, IntegerChoices):
    # In Finnish: "ILMAN PERÄKIINNITYSTÄ"
    NO_STERN_TO_MOORING = 1, _("No stern-to mooring")
    # In Finnish: "AISAPAIKKA"
    SINGLE_SLIP_PLACE = 2, _("Single slip place")
    # In Finnish: "KÄVELYAISAPAIKKA"
    SIDE_SLIP_PLACE = 3, _("Side slip place")
    # In Finnish: "PERÄPOIJUPAIKKA"
    STERN_BUOY_PLACE = 4, _("Stern buoy place")
    # In Finnish: "PAALUPERÄKIINNITYS"
    STERN_POLE_MOORING = 5, _("Stern pole mooring")
    # In Finnish: "SIVUKIINNITYS"
    QUAYSIDE_MOORING = 6, _("Quayside mooring")
    # In Finnish: "JOLLAPAIKKA"
    DINGHY_PLACE = 7, _("Dinghy place")
    # In Finnish: "POIJU (MERELLÄ)"
    SEA_BUOY_MOORING = 8, _("Sea buoy mooring")
    # In Finnish: "TRAILERIPAIKKA"
    TRAWLER_PLACE = 9, _("Trawler place")


class AreaRegion(ChoicesMixin, TextChoices):
    EAST = "east", _("East")
    WEST = "west", _("West")
