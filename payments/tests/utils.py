import random
from decimal import Decimal

from utils.numbers import random_decimal

from ..utils import _get_vasikkasaari_harbor, rounded


@rounded
def random_price(lower=0.1, upper=999, decimals=2) -> Decimal:
    # Generate a random float with the given number of decimals
    # (allowing to generate price values without decimals, i.e. Decimal("73.00")).
    return random_decimal(min=lower, max=upper, decimals=decimals)


@rounded
def random_tax(min=0, max=100, decimals=0) -> Decimal:
    return random_decimal(min=min, max=max, decimals=decimals)


def random_bool():
    return bool(random.getrandbits(1))


def get_berth_lease_pricing_category(lease):
    from payments.enums import PricingCategory
    from resources.enums import BerthMooringType

    mooring_type = lease.berth.berth_type.mooring_type

    if mooring_type == BerthMooringType.DINGHY_PLACE:
        return PricingCategory.DINGHY

    if mooring_type == BerthMooringType.TRAWLER_PLACE:
        return PricingCategory.TRAILER

    if lease.berth.pier.harbor == _get_vasikkasaari_harbor():
        return PricingCategory.VASIKKASAARI

    return PricingCategory.DEFAULT
