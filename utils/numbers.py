from decimal import Decimal
from random import uniform
from typing import Union

DecimalString = Union[Decimal, str]


def rounded(
    value: Union[Decimal, int, float, str], decimals: int = 2, as_string: bool = False
) -> DecimalString:
    """
    Round a decimal to a given amount of decimals and return it as either Decimal or String

    :param value: The number to round
    :param decimals: The amount of decimals to round value
    :param as_string: Whether the value should be returned as Decimal or string.
    For testing, it's useful to be able to parse the Decimal value directly to string.
    :return: A rounded Decimal number
    """
    number = round(Decimal(value), decimals)

    return str(number) if as_string else number


def random_decimal(
    min: float = 0, max: float = 100, decimals: int = 2, as_string: bool = False
) -> DecimalString:
    return rounded(uniform(min, max), decimals=decimals, as_string=as_string)
