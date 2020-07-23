from decimal import Decimal
from random import uniform
from typing import Union

DecimalString = Union[Decimal, str]


def rounded(
    value: Union[Decimal, int, float, str],
    decimals: int = 2,
    as_string: bool = False,
    round_to_nearest: Union[Decimal, float] = None,
) -> DecimalString:
    """
    Round a decimal to a given amount of decimals and return it as either Decimal or String

    :param value: The number to round
    :param decimals: The amount of decimals to round value
    :param as_string: Whether the value should be returned as Decimal or string.
    For testing, it's useful to be able to parse the Decimal value directly to string.
    :param round_to_nearest: Rounds the value to the nearest decimal passed.
    I.e. the nearest 0.05 of 3.1416 -> 3.15
    :return: A rounded Decimal number
    """
    if round_to_nearest:
        correction = Decimal(0.5 if value >= 0 else -0.5)
        value = Decimal(
            int(value / Decimal(round_to_nearest) + correction)
            * Decimal(round_to_nearest)
        )

    value = round(Decimal(value), decimals)

    return str(value) if as_string else value


def random_decimal(
    min: float = 0, max: float = 100, decimals: int = 2, as_string: bool = False
) -> DecimalString:
    return rounded(uniform(min, max), decimals=decimals, as_string=as_string)
