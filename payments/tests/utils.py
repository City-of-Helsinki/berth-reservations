import random
from decimal import Decimal

from payments.utils import rounded


@rounded
def random_price(lower=0.1, upper=999, decimals=2):
    # Generate a random float with the given number of decimals
    # (allowing to generate price values without decimals, i.e. Decimal("73.00")).
    return Decimal(round(random.uniform(lower, upper), decimals))


@rounded
def random_tax(min=0, max=100):
    return Decimal(random.randint(min, max))


def random_bool():
    return bool(random.getrandbits(1))
